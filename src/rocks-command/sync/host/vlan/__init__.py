# $Id: __init__.py,v 1.6 2012/11/27 00:49:11 phil Exp $
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
#
#

import os
import time
import rocks.commands
import rocks.vmextended

class Command(rocks.commands.sync.host.command):
	"""
	Start the vlan interface needed by virtual 
	machines on a vm-containers and on frontends.
	VLan used by virtual machines now are not anymore under
	Red Hat network manager control, but they are started 
	automatically by this command.
	

	<example cmd='sync host vlan compute-0-0-0'>
	Start the vlan needed by the virtual host compute-0-0-0
	If the vrtual host does not use any vlan the command does nothing
	</example>
	"""


	def startUpNetwork(self, physhost, host):
		"""start up Vlan interface on the physhost 
		if the host is using any of them 
		Vlan are not managed anymore by the Redhat 
		network scripts"""

		#get the vlanid of the VM
		self.db.execute("""select net.vlanid
			from networks net, nodes n
			where net.node = n.id and net.vlanid > 0 
			and n.name = "%s" """ % (host))
		for row in self.db.fetchall():
			vlanid= row[0]

			#given the vlanid get the network device on the dom0 
			self.db.execute("""select distinctrow net.device, net.subnet, 
				net.module, s.mtu, net.options, net.channel
				from networks net, nodes n, subnets s 
				where net.node = n.id and if(net.subnet, net.subnet = s.id, true) and
				n.name = "%s" and net.vlanid = %s order by net.id""" % (physhost, vlanid))

			for row in self.db.fetchall():
				(device, subnetid, module, mtu, options, channel) = row
				#print "device: ", device, vlanid
				#
				# look up the name of the interface that
				# maps to this VLAN spec
				#
				rows = self.db.execute("""select net.device from
					networks net, nodes n where
					n.id = net.node and n.name = '%s'
					and net.subnet = %d and
					net.device not like 'vlan%%' """ %
					(physhost, subnetid))
				
				if rows:
					dev, = self.db.fetchone()
					#
					# check if already referencing 
					# a physical device
					#
					if dev != device:
						device = 'p' + dev
				else:
					self.abort('Unable to get device name for dev: ', device)

				#
				# let's check if the device is already up
				#
				ret = os.system("ssh %s ip link show %s.%s > /dev/null 2>&1 " % 
						(physhost, device, vlanid))
				if ret != 0:
					#
					# the vlan is down let's activate it
					#
					ret = os.system(("ssh %s \"vconfig add %s %s; ifconfig %s.%s up; " +
							" ip link set arp off dev %s.%s\" ") % 
							(physhost, device, vlanid, device, vlanid, device, vlanid))
					if ret != 0:
						self.abort('Unable to instantiate vlan ' + str(vlanid) + \
							' on device ' + device)
			
	
	def run(self, params, args):
		hosts = self.getHostnames(args, managed_only=1)

		if len(hosts) < 1:
			self.abort('must supply at least one host')

		for host in hosts:
			#
			# the name of the physical host that will boot
			# this VM host
			#
			vm = rocks.vmextended.VMextended(self.db)
			(physnodeid, physhost) = vm.getPhysNode(host)

			if not physhost or not physnodeid:
				self.abort("Could not determine the physical host"
					"Error host %s must be a virtual host" % host)

			self.startUpNetwork(physhost, host)


