# $Id: __init__.py,v 1.10 2013/01/30 19:27:35 clem Exp $
#
# @Copyright@
# 
# 				Rocks(r)
# 		         www.rocksclusters.org
# 		         version 5.6 (Emerald Boa)
# 		         version 6.1 (Emerald Boa)
# 
# Copyright (c) 2000 - 2013 The Regents of the University of California.
# All rights reserved.	
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
# notice unmodified and in its entirety, this list of conditions and the
# following disclaimer in the documentation and/or other materials provided 
# with the distribution.
# 
# 3. All advertising and press materials, printed or electronic, mentioning
# features or use of this software must display the following acknowledgement: 
# 
# 	"This product includes software developed by the Rocks(r)
# 	Cluster Group at the San Diego Supercomputer Center at the
# 	University of California, San Diego and its contributors."
# 
# 4. Except as permitted for the purposes of acknowledgment in paragraph 3,
# neither the name or logo of this software nor the names of its
# authors may be used to endorse or promote products derived from this
# software without specific prior written permission.  The name of the
# software includes the following terms, and any derivatives thereof:
# "Rocks", "Rocks Clusters", and "Avalanche Installer".  For licensing of 
# the associated name, interested parties should contact Technology 
# Transfer & Intellectual Property Services, University of California, 
# San Diego, 9500 Gilman Drive, Mail Code 0910, La Jolla, CA 92093-0910, 
# Ph: (858) 534-5815, FAX: (858) 534-7345, E-MAIL:invent@ucsd.edu
# 
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS''
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# @Copyright@
#

import os
import stat
import tempfile
import rocks.commands
import rocks.vmextended
import re

import sys
sys.path.append('/usr/lib64/python2.' + str(sys.version_info[1]) + '/site-packages')
sys.path.append('/usr/lib/python2.' + str(sys.version_info[1]) + '/site-packages')
import libvirt

class Command(rocks.commands.report.host.command):
	"""
	Reports the XML Configuration for VM that will be handed
	to libvirt for startup.	

	<arg type='string' name='host' repeat='1'>
	One or more VM host names.
	</arg>

	<example cmd='report host vm config compute-0-0-0'>
	list the XML configuration of Report XML Config of VM compute-0-0-0.
	</example>

	"""

	def getBridgeDevName(self, host, subnetid, vlanid):
		returnDeviceName = None

		if vlanid:
			#
			# first make sure the vlan is defined for the physical
			# host and get the logical subnet where the vlan is tied
			#
			rows = self.db.execute("""select net.subnet from
				networks net, nodes n where net.node = n.id and
				n.name = '%s' and (net.device like 'vlan%%' or
				net.device like '%%.%d') and
				net.vlanid = %d""" % (host, vlanid, vlanid))

			if rows == 0:
				self.abort('vlan %d not defined for host %s' %
					(vlanid, host))
			vlanOnLogical, = self.db.fetchone()

			rows = self.db.execute("""select net.device from
				networks net, nodes n where net.node = n.id
				and n.name = '%s' and
				net.device not like 'vlan%%' and
				net.subnet = %d""" % (host, vlanOnLogical))
		else:
			rows = self.db.execute("""select net.device from
				networks net, nodes n where net.node = n.id and
				n.name = '%s' and net.ip is not NULL and
				net.device not like 'vlan%%' and
				net.subnet = %d""" % (host, subnetid))
		if rows:
			dev, = self.db.fetchone()
			returnDeviceName = dev
			if vlanid:
				reg = re.compile('.*\.%d' % vlanid)
				if not reg.match(dev):
					#we have to add the vlan tag to the device
					returnDeviceName = '%s.%d' % (dev, vlanid)
		return returnDeviceName


	def reportBootLoader(self, host, xmlconfig, virtType, cdrom):
		"""first section of the libvirt xml with the startup params"""

		xmlconfig.append("<domain type='kvm'>")
		xmlconfig.append("<name>%s</name>" % host)
		xmlconfig.append("<os>")
		xmlconfig.append("  <type>hvm</type>")

		#print "host is ", host
                #let's check out the boot action
		nrows = self.db.execute("""select b.action from boot b , nodes n where
			b.node = n.id and n.name = "%s" """ % (host))
		if nrows < 1:
			#that's bad!
			self.abort('Host ' + host + ' doesn\'t have a boot action...')
		else:
			action, = self.db.fetchone()


		#let's see how we boot this VM
		runAction = None
		installAction = None
		rows = self.db.execute("""select runaction, installaction
			from nodes where name = '%s' """ % host)
		if rows > 0:
			(runAction, installAction) = self.db.fetchone()
		if installAction == "install vm frontend" and action == 'install':
			#action == 'install' and installAction == install vm fronend
			#aka we are installing a frontend
			#1. anaconda kernel and ramdisk
			#2. network info to fetch stage2 from http server
			# Read the profile
			kernel, ramdisk, bootargs = ('', '', '')
			rows = self.db.execute("""select kernel, ramdisk, args
					from bootaction where action = '%s' """ % installAction)
			if rows > 0:
				kernel, ramdisk, bootargs = self.db.fetchone()

			ip = None
			netmask = None
			dns = None
			gateway = None
			if host in self.getHostnames( [ 'frontend' ]):
				subnet = 'public'
				rows = self.db.execute("""select net.ip, s.netmask from
				        networks net,
				        nodes n, subnets s where n.name='%s' and
				        n.id = net.node and net.subnet = s.id and
				        s.name = '%s' """ % (host, subnet))
				
				if rows > 0:
					(ip, netmask) = self.db.fetchone()
				
				dns = self.db.getHostAttr(host,
					'Kickstart_PublicDNSServers')
				
				for (key, val) in self.db.getHostRoutes(host).items():
					if key == '0.0.0.0' and val[0] == '0.0.0.0':
						gateway = val[1]
			
			if ip:
				bootargs += ' ip=%s ' % ip
			if netmask:
				bootargs += ' netmask=%s ' % netmask
			if dns:
			        #
			        # the user can enter in multiple DNS servers that are
			        # separated by a comma. we can only supply one DNS
			        # to anaconda, so let's just select the first one.
			        #
			        bootargs += ' dns=%s ' % dns.split(',')[0]
			if gateway:
			        bootargs += ' gateway=%s ' % gateway
			
			xmlconfig.append("  <kernel>%s</kernel>" % kernel )
			xmlconfig.append("  <initrd>%s</initrd>" % ramdisk )
			xmlconfig.append("  <cmdline>%s</cmdline>" % bootargs )
			xmlconfig.append("</os>")
			xmlconfig.append("<on_reboot>destroy</on_reboot>")
		else:
			#we boot the machine as if normal hardware
			xmlconfig.append("  <boot dev='network'/>")
			xmlconfig.append("  <boot dev='hd'/>")
			if cdrom :
				xmlconfig.append("  <boot dev='cdrom'/>")
			xmlconfig.append("  <bootmenu enable='yes'/>")
			xmlconfig.append("</os>")


	def getXMLconfig(self, physhost, host):

		xmlconfig = []
		cdrom_path = self.vm.getCDROM(host)
		virtType = self.command('report.host.vm.virt_type', [ host,]).strip()
		self.reportBootLoader(host,xmlconfig,virtType, cdrom_path)

		#
		# get the VM parameters
		#
		vmnodeid = None
		mem = None
		cpus = None
		slice = None
		macs = None
		disks = None

		rows = self.db.execute("""select vn.id, vn.mem, n.cpus
			from nodes n, vm_nodes vn where vn.node = n.id and
			n.name = '%s'""" % host)

		vmnodeid, mem, cpus = self.db.fetchone()
		if not vmnodeid or not mem or not cpus:
			return

		try:
			memory = int(mem) * 1024
		except:
			return

		xmlconfig.append("<memory>%s</memory>" % memory)	
		xmlconfig.append("<vcpu>%s</vcpu>" % cpus)	

                # cpu_mode you can specify the capabilities of the virtual cpu
                # host-passthrough should be the default for speed
                cpu_mode = self.db.getHostAttr(host, 'cpu_mode')
                cpu_match = self.db.getHostAttr(host, 'cpu_match')
                if cpu_mode :
                        xmlconfig.append("<cpu mode='" + 
				self.unescapeAttr(cpu_mode) + "'/>")
                elif cpu_match :
			cpu_match = self.unescapeAttr(cpu_match)
                        cpu_match_split = cpu_match.split(':', 1)
                        xmlconfig.append("<cpu mode='" + cpu_match_split[0] + "'>")
                        if len(cpu_match_split) > 1 :
                                xmlconfig.append( cpu_match_split[1] )
                        xmlconfig.append("</cpu>")

		# for cpu pinning
		attribute = self.db.getHostAttr(host, 'kvm_cpu_pinning')
		if attribute == "pin_all":
			xmlconfig.append("<cputune>")
			for i in range(cpus):
			        xmlconfig.append("  <vcpupin vcpu=\"%d\" cpuset=\"%d\"/>" % (i, i))
			xmlconfig.append("</cputune>")
		elif attribute:
			xmlconfig.append(self.unescapeAttr(attribute))

		if virtType == 'hvm':
			features = self.db.getHostAttr(host,'HVM_Features')
			if features is None :
				features = """\t<acpi/>\n\t<apic/>\n\t<pae/>"""
			xmlconfig.append("<features>")
			xmlconfig.append(self.unescapeAttr(features))
			xmlconfig.append("</features>")

		#
		# configure the devices
		#
		xmlconfig.append("<devices>")
		xmlconfig.append("  <emulator>/usr/libexec/qemu-kvm</emulator>")

		#
		# network config
		#
		rows = self.db.execute("""select net.mac, net.subnet, net.vlanid
			from networks net, nodes n, vm_nodes vn
			where vn.node = n.id and net.node = n.id and
			n.name = '%s' order by net.id""" % host)

		macs = self.db.fetchall()
		if not macs:
			return

		vifs = []
		index = 0
		for mac, subnetid, vlanid in macs:
			# allow VMs to have virtual and VLAN interfaces
			if mac is not None:
				# we need to understand if it is a directly attached interface 
				# (macvtap) or a bridged interface 
				#
				# if it is directly attached there should be an interface 
				# named vlan<vlanid> if it's bridged there should be an 
				# interface on the vlanid with an IP address or not vlanID
				# 
				bridged = False
				if not vlanid :
					bridged = True
				else:
					rows = self.db.execute("""select net.device, net.ip
						from networks net, nodes n
						where net.node = n.id and
						n.name = '%s' and net.vlanid = %d""" % 
						(physhost, vlanid))
	
					if rows  > 1 :
						self.abort("There are too many interfaces defined on %s with vlan %d" %
							(physhost, vlanid))
	
					if rows == 0 :
						self.abort("There no interface defined on %s with vlan %d" %
							(physhost, vlanid))
	
					physDevName, physDevIP = self.db.fetchone()

					if physDevIP == None and 'vlan' in physDevName :
						bridged = False
					else:
						bridged = True

				if not bridged:
					xmlconfig.append("  <interface type='direct'>")
					dev = self.getBridgeDevName(physhost, subnetid, vlanid)
					xmlconfig.append("    <source dev='p%s' mode='bridge'/>" % dev )
					xmlconfig.append("    <mac address='%s'/>" % mac)
					xmlconfig.append("    <model type='virtio' />")
					xmlconfig.append("  </interface>")
				else:
					xmlconfig.append("  <interface type='bridge'>")
					#xmlconfig.append("  <interface type='direct'>")
					dev = self.getBridgeDevName(physhost, subnetid, vlanid)
					xmlconfig.append("    <source bridge='%s'/>" % dev )
					#xmlconfig.append("    <source dev='%s' mode='bridge'/>" % dev )
					xmlconfig.append("    <mac address='%s'/>" % mac)
					xmlconfig.append("    <model type='virtio' />")
					xmlconfig.append("  </interface>")
				index += 1

		#
		# disk config
		#
		rows = self.db.execute("""select vbd_type, prefix, name,
			device, mode, size from vm_disks where vm_node = %s
			order by id""" % vmnodeid)
		disks = self.db.fetchall()
		if not disks:
			return

		vmdisks = []
		index = 0
		bootdisk = None
		bootdevice = None
		idedevices = []
		for vbd_type,prefix,name,device,mode,size in disks:
			#
			# if the disk specification is a 'regular' file, then
			# make sure the file for the disk space exists. if
			# it doesn't, create a sparse file for the disk space.
			#
			file = os.path.join(prefix, name)

			if vbd_type in [ 'file', 'qcow2', 'qed' ]:
				a = "<disk type='file' device='disk'>"
				xmlconfig.append(a)

				if vbd_type == 'file':
					#default
					a = "<driver name='qemu' type='raw'/>"
				elif vbd_type == 'qcow2':
					a = "<driver name='qemu' type='qcow2'/>"
				elif vbd_type == 'qed':
					a = "<driver name='qemu' type='qed'/>"
				xmlconfig.append(a)
				#elif vbd_type == 'tap:aio':
				#	a = "<driver name='tap' type='aio'/>"

				a = "<source file='%s'/>" % file
				xmlconfig.append(a)

			elif vbd_type == 'phy':
				a = "<disk type='block' device='disk'>"
				xmlconfig.append(a)

				a = "<source dev='%s'/>" % file
				xmlconfig.append(a)
			else:
				self.abort("Disk type is not valid. Please see rocks add host vm help.")

			# we misuse the mode column to carry the driver name 
			# that needs to should be used to expese the disk 
			if mode == 'w':
				# default driver
				# legacy for backward compatibility
				bus = 'virtio'
			else:
				bus = mode

			a = "<target dev='%s' bus='%s'/>" % (device, bus)
			if device == 'ide':
				idedevices.append(device)
			xmlconfig.append(a)

			a = "</disk>"
			xmlconfig.append(a)

		#
		# check for a CDROM
		#
		if cdrom_path:
			xmlconfig.append("<disk type='file' device='cdrom'>")
			xmlconfig.append("  <driver name='qemu' type='raw'/>")
			if stat.S_ISBLK(os.stat(cdrom_path).st_mode):
				# block device
				xmlconfig.append("  <source dev='%s'/>" % cdrom_path)
			elif stat.S_ISREG(os.stat(cdrom_path).st_mode):
				xmlconfig.append("  <source file='%s'/>" % cdrom_path)
			else:
				self.abort("cdrom does not point to a valid path. "
					"Change it with rocks set host vm cdrom")
			# find the ide device
			for i in ['a', 'b', 'c', 'd']:
				device = 'hd' + i
				if device not in idedevices:
					break
			xmlconfig.append("  <target dev='%s' bus='ide'/>"% device)
			xmlconfig.append("  <readonly/>")
			xmlconfig.append("</disk>")

		#
		# additional devices set with attributes
		#
		i = 0
		while True:
			attribute = self.db.getHostAttr(host, 'kvm_device_%d' % i)
			i = i + 1
			if attribute :
				xmlconfig.append(self.unescapeAttr(attribute))
			else:
				break

		#
		# the extra devices
		#
		xmlconfig.append("<graphics type='vnc' port='-1'/>")
		xmlconfig.append("<console tty='/dev/pts/0'/>")
		xmlconfig.append("</devices>")
		xmlconfig.append("</domain>")
		return '\n'.join(xmlconfig)



	def run(self, params, args):
		hosts = self.getHostnames(args)

		if len(hosts) < 1:
			self.abort('must supply at least one host')

		self.beginOutput()
		for host in hosts:
			#
			# get the VM configuration (in XML format for libvirt)
			#
			self.vm = rocks.vmextended.VMextended(self.db)
			(physnodeid, physhost) = self.vm.getPhysNode(host)
			if not physhost:
				continue
			xmlconfig = self.getXMLconfig(physhost, host)
			self.addOutput(host, '%s' % xmlconfig)
		self.endOutput(padChar='')



