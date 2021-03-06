#
# @Copyright@
# 
# 				Rocks(r)
# 		         www.rocksclusters.org
# 		         version 6.2 (SideWinder)
# 
# Copyright (c) 2000 - 2014 The Regents of the University of California.
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


REDHAT.ROOT     = $(PWD)/../../
PKGROOT		= /opt/rocks
-include $(ROCKSROOT)/etc/Rules.mk
include Rules.mk

# we need this to disable the stupid 
# /usr/lib/rpm/brp-python-bytecompile
# which just does a big mess in compiling all the python files
MAKE.rpmflag	= -bb --define "__spec_install_post :"


# if ROOT is not defined assign / so that 
# python setup.py install --root=$(ROOT)
# has always something after the = if not distutils 
# will bail on you
ROOT ?= /


build:

install::
	find rocks | sed -e 's/\//./g' -e '/\.py/d' -e '/\.sql/d' > packages
	$(PY.PATH) setup.py install -f --root=$(ROOT)


clean::
	rm -rf build
	rm -rf dist
	rm -rf rocks_command_kvm.egg-info
	rm -rf packages


ctags:
	ctags  --python-kinds=-i --exclude=*/build/* -R .

# add the RollName = "base" variable to all the command files we can 
# commit this into the repo since this property never changes
#
# this script is a helper for adding the variable to all the file in 
# this package
addrollvariable:
	for i in `find rocks/commands -name "*.py"`; do\
		grep "^RollName = " $$i > /dev/null ||                  \
		echo -e "\nRollName = \"$(ROLL)\"" >> $$i;              \
	done
 


