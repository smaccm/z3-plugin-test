#!/usr/local/bin/python2.7
# encoding: utf-8
'''
Detect released versions of Z3 Prover and package as Eclipse plugin

This module uses the Github API v3 to query the released versions of
Microsoft Z3 Prover.  For the detected releases the binaries are packaged
as an Eclipse plugin.  Optionally, a list of versions in a file are skipped.
Also, versions already packaged are skipped as well.

@copyright:  2019 Collins Aerospace. All rights reserved.

@license:    MIT License
'''

import os
import re
import requests
import subprocess
import sys
import tempfile

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from git import Repo
from macholib.MachOGraph import MachOGraph
from pprint import pprint
from shutil import copyfile
from string import Template
from zipfile import ZipFile

POM_TEMPLATE = Template('''<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.collins.trustedsystems.z3</groupId>
    <version>${plugin_version}</version>
    <artifactId>com.collins.trustedsystems.z3.parent</artifactId>
    <packaging>pom</packaging>

    <properties>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <maven.compiler.source>1.8</maven.compiler.source>
        <maven.compiler.target>1.8</maven.compiler.target>
        <!-- Tycho settings -->
        <tycho.version>1.3.0</tycho.version>
        <tycho-extras.version>1.3.0</tycho-extras.version>
        <eclipse.mirror>http://download.eclipse.org</eclipse.mirror>
        <emf-version>2.15.0</emf-version>
        <emf-common-version>2.15.0</emf-common-version>
        <emf-codegen-version>2.15.0</emf-codegen-version>
        <ecore-xtext-version>1.4.0</ecore-xtext-version>
        <ecore-xcore-version>1.8.0</ecore-xcore-version>
        <ecore-xcore-lib-version>1.3.0</ecore-xcore-lib-version>
    </properties>
    <modules>
        <module>com.collins.trustedsystems.z3</module>
        <module>com.collins.trustedsystems.z3.linux.gtk.x86_64</module>
        <module>com.collins.trustedsystems.z3.macosx.cocoa.x86_64</module>
        <module>com.collins.trustedsystems.z3.win32.win32.x86_64</module>
        <module>com.collins.trustedsystems.z3.feature</module>
        <module>com.collins.trustedsystems.z3.target</module>
        <module>com.collins.trustedsystems.z3.repository</module>
    </modules>
    <build>
        <plugins>
            <plugin>
                <groupId>org.eclipse.tycho</groupId>
                <artifactId>tycho-maven-plugin</artifactId>
                <version>$${tycho.version}</version>
                <extensions>true</extensions>
            </plugin>
            <plugin>
                <groupId>org.eclipse.tycho</groupId>
                <artifactId>tycho-source-plugin</artifactId>
                <version>$${tycho.version}</version>
                <executions>
                    <execution>
                        <id>plugin-source</id>
                        <goals>
                            <goal>plugin-source</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
            <plugin>
                <groupId>org.eclipse.tycho</groupId>
                <artifactId>tycho-p2-plugin</artifactId>
                <version>$${tycho.version}</version>
                <executions>
                    <execution>
                        <id>attach-p2-metadata</id>
                        <phase>package</phase>
                        <goals>
                            <goal>p2-metadata</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
            <plugin>
                <groupId>org.eclipse.tycho</groupId>
                <artifactId>target-platform-configuration</artifactId>
                <version>$${tycho.version}</version>
                <configuration>
                    <target>
                        <artifact>
                            <groupId>com.collins.trustedsystems.z3</groupId>
                            <artifactId>com.collins.trustedsystems.z3.target</artifactId>
                            <version>${plugin_version}</version>
                        </artifact>
                    </target>
                    <environments>
                        <environment>
                            <os>win32</os>
                            <ws>win32</ws>
                            <arch>x86_64</arch>
                        </environment>
                        <environment>
                            <os>linux</os>
                            <ws>gtk</ws>
                            <arch>x86_64</arch>
                        </environment>
                        <environment>
                            <os>macosx</os>
                            <ws>cocoa</ws>
                            <arch>x86_64</arch>
                        </environment>
                    </environments>
                </configuration>
            </plugin>
        </plugins>
        <pluginManagement>
            <plugins>
                <plugin>
                    <groupId>org.apache.maven.plugins</groupId>
                    <artifactId>maven-clean-plugin</artifactId>
                    <version>2.5</version>
                    <configuration>
                        <filesets>
                            <fileset>
                                <directory>$${basedir}/xtend-gen</directory>
                                <includes>
                                    <include>**/*</include>
                                </includes>
                            </fileset>
                        </filesets>
                    </configuration>
                </plugin>
                <plugin>
                    <groupId>org.eclipse.m2e</groupId>
                    <artifactId>lifecycle-mapping</artifactId>
                    <version>1.0.0</version>
                    <configuration>
                        <lifecycleMappingMetadata>
                            <pluginExecutions>
                                <pluginExecution>
                                    <pluginExecutionFilter>
                                        <groupId>
                                            org.apache.maven.plugins
                                        </groupId>
                                        <artifactId>
                                            maven-resources-plugin
                                        </artifactId>
                                        <versionRange>
                                            [2.4.3,)
                                        </versionRange>
                                        <goals>
                                            <goal>resources</goal>
                                            <goal>testResources</goal>
                                        </goals>
                                    </pluginExecutionFilter>
                                    <action>
                                        <ignore></ignore>
                                    </action>
                                </pluginExecution>
                                <pluginExecution>
                                    <pluginExecutionFilter>
                                        <groupId>
                                            org.codehaus.mojo
                                        </groupId>
                                        <artifactId>
                                            build-helper-maven-plugin
                                        </artifactId>
                                        <versionRange>
                                            [1.9.1,)
                                        </versionRange>
                                        <goals>
                                            <goal>add-resource</goal>
                                            <goal>add-source</goal>
                                            <goal>add-test-resource</goal>
                                            <goal>add-test-source</goal>
                                        </goals>
                                    </pluginExecutionFilter>
                                    <action>
                                        <ignore></ignore>
                                    </action>
                                </pluginExecution>
                                <pluginExecution>
                                    <pluginExecutionFilter>
                                        <groupId>
                                            org.eclipse.tycho
                                        </groupId>
                                        <artifactId>
                                            tycho-compiler-plugin
                                        </artifactId>
                                        <versionRange>
                                            [0.23.1,)
                                        </versionRange>
                                        <goals>
                                            <goal>compile</goal>
                                        </goals>
                                    </pluginExecutionFilter>
                                    <action>
                                        <ignore></ignore>
                                    </action>
                                </pluginExecution>
                                <pluginExecution>
                                    <pluginExecutionFilter>
                                        <groupId>
                                            org.eclipse.tycho
                                        </groupId>
                                        <artifactId>
                                            tycho-packaging-plugin
                                        </artifactId>
                                        <versionRange>
                                            [0.23.1,)
                                        </versionRange>
                                        <goals>
                                            <goal>build-qualifier</goal>
                                            <goal>build-qualifier-aggregator</goal>
                                            <goal>validate-id</goal>
                                            <goal>validate-version</goal>
                                        </goals>
                                    </pluginExecutionFilter>
                                    <action>
                                        <ignore></ignore>
                                    </action>
                                </pluginExecution>
                            </pluginExecutions>
                        </lifecycleMappingMetadata>
                    </configuration>
                </plugin>
                <plugin>
                    <!-- 
                        Can be removed after first generator execution
                        https://bugs.eclipse.org/bugs/show_bug.cgi?id=480097
                    -->
                    <groupId>org.eclipse.tycho</groupId>
                    <artifactId>tycho-compiler-plugin</artifactId>
                    <version>$${tycho.version}</version>
                    <configuration>
                        <compilerArgument>-err:-forbidden</compilerArgument>
                        <useProjectSettings>false</useProjectSettings>
                    </configuration>
                </plugin>
            </plugins>
        </pluginManagement>
    </build>
    <repositories>
        <!-- add Eclipse repository to resolve dependencies -->
        <repository>
            <id>Eclipse</id>
            <layout>p2</layout>
            <url>$${eclipse.mirror}/releases/photon/</url>
        </repository>
        <repository>
            <id>codehaus-snapshots</id>
            <name>disable dead 'Codehaus Snapshots' repository, see https://bugs.eclipse.org/bugs/show_bug.cgi?id=481478</name>
            <url>http://nexus.codehaus.org/snapshots/</url>
            <releases>
                <enabled>false</enabled>
            </releases>
            <snapshots>
                <enabled>false</enabled>
            </snapshots>
        </repository>
    </repositories>
    <pluginRepositories>
        <pluginRepository>
            <id>codehaus-snapshots</id>
            <name>disable dead 'Codehaus Snapshots' repository, see https://bugs.eclipse.org/bugs/show_bug.cgi?id=481478</name>
            <url>http://nexus.codehaus.org/snapshots/</url>
            <releases>
                <enabled>false</enabled>
            </releases>
            <snapshots>
                <enabled>false</enabled>
            </snapshots>
        </pluginRepository>
    </pluginRepositories>
    <profiles>
        <profile>
            <id>macos</id>
            <activation>
                <os>
                    <family>mac</family>
                </os>
            </activation>
            <properties>
                <!-- THE FOLLOWING LINE MUST NOT BE BROKEN BY AUTOFORMATTING -->
                <platformSystemProperties>-XstartOnFirstThread</platformSystemProperties>
            </properties>
        </profile>
        <profile>
            <id>jdk9-or-newer</id>
            <activation>
                <jdk>[9,)</jdk>
            </activation>
            <properties>
                <moduleProperties>--add-modules=ALL-SYSTEM</moduleProperties>
            </properties>
        </profile>
    </profiles>

    <dependencies>
        <dependency>
            <groupId>org.eclipse.emf</groupId>
            <artifactId>org.eclipse.emf.common</artifactId>
            <version>$${emf-common-version}</version>
        </dependency>

        <dependency>
            <groupId>org.eclipse.emf</groupId>
            <artifactId>org.eclipse.emf.ecore</artifactId>
            <version>$${emf-version}</version>
        </dependency>

        <dependency>
            <groupId>org.eclipse.emf</groupId>
            <artifactId>org.eclipse.emf.ecore.xcore.lib</artifactId>
            <version>$${ecore-xcore-lib-version}</version>
        </dependency>

    </dependencies>
</project>
''')

SOURCE_POM_TEMPLATE = Template('''<?xml version="1.0" encoding="UTF-8"?>
<project
    xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd"
    xmlns="http://maven.apache.org/POM/4.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.collins.trustedsystems.z3</groupId>
        <artifactId>com.collins.trustedsystems.z3.parent</artifactId>
        <version>${plugin_version}</version>
    </parent>
    <artifactId>com.collins.trustedsystems.z3</artifactId>
    <packaging>eclipse-plugin</packaging>
</project>
''')

SOURCE_MANIFEST_TEMPLATE = Template('''Manifest-Version: 1.0
Bundle-ManifestVersion: 2
Bundle-Name: Z3 Plugin
Bundle-SymbolicName: com.collins.trustedsystems.z3
Bundle-Version: ${plugin_version}
Bundle-Activator: com.collins.trustedsystems.z3.Activator
Bundle-Vendor: Collins Aerospace
Require-Bundle: org.eclipse.core.runtime
Bundle-RequiredExecutionEnvironment: JavaSE-1.8
Bundle-ActivationPolicy: lazy
Export-Package: com.collins.trustedsystems.z3
Automatic-Module-Name: com.collins.trustedsystems.z3
''')

FEATURE_POM_TEMPLATE = Template('''<?xml version="1.0" encoding="UTF-8"?>
<project
    xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd"
    xmlns="http://maven.apache.org/POM/4.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.collins.trustedsystems.z3</groupId>
        <artifactId>com.collins.trustedsystems.z3.parent</artifactId>
        <version>${plugin_version}</version>
    </parent>
    <artifactId>com.collins.trustedsystems.z3.feature</artifactId>
    <packaging>eclipse-feature</packaging>

    <build>
        <plugins>
            <!-- source feature generation -->
            <plugin>
                <groupId>org.eclipse.tycho.extras</groupId>
                <artifactId>tycho-source-feature-plugin</artifactId>
                <version>$${tycho-extras.version}</version>
                <executions>
                    <execution>
                        <id>source-feature</id>
                        <phase>package</phase>
                        <goals>
                            <goal>source-feature</goal>
                        </goals>
                    </execution>
                </executions>
                <configuration>
                    <excludes>
                        <plugin id="com.collins.trustedsystems.z3.linux.gtk.x86_64" />
                        <plugin id="com.collins.trustedsystems.z3.macosx.cocoa.x86_64" />
                        <plugin id="com.collins.trustedsystems.z3.win32.win32.x86_64" />
                    </excludes>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.eclipse.tycho</groupId>
                <artifactId>tycho-p2-plugin</artifactId>
                <version>$${tycho.version}</version>
                <executions>
                    <execution>
                        <id>attach-p2-metadata</id>
                        <phase>package</phase>
                        <goals>
                            <goal>p2-metadata</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>
''')

FEATURE_XML_TEMPLATE = Template('''<?xml version="1.0" encoding="UTF-8"?>
<feature
      id="com.collins.trustedsystems.z3.feature"
      label="Z3 Plugin"
      version="${plugin_version}"
      provider-name="Collins Aerospace">

   <description url="https://github.com/smaccm/z3-plugins">
      Z3 Plugins for Eclipse
   </description>

   <copyright url="https://github.com/Z3Prover/z3">
      Z3
Copyright (c) Microsoft Corporation
All rights reserved.
   </copyright>

   <license url="https://github.com/Z3Prover/z3">
      Z3
Copyright (c) Microsoft Corporation
All rights reserved. 
MIT License
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the &quot;&quot;Software&quot;&quot;), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
   </license>

   <plugin
         id="com.collins.trustedsystems.z3"
         download-size="0"
         install-size="0"
         version="${plugin_version}"
         unpack="false"/>

   <plugin
         id="com.collins.trustedsystems.z3.linux.gtk.x86_64"
         os="linux"
         ws="gtk"
         arch="x86_64"
         download-size="0"
         install-size="0"
         version="${plugin_version}"
         fragment="true"/>

   <plugin
         id="com.collins.trustedsystems.z3.macosx.cocoa.x86_64"
         os="macosx"
         ws="cocoa"
         arch="x86_64"
         download-size="0"
         install-size="0"
         version="${plugin_version}"
         fragment="true"/>

   <plugin
         id="com.collins.trustedsystems.z3.win32.win32.x86_64"
         os="win32"
         ws="win32"
         arch="x86_64"
         download-size="0"
         install-size="0"
         version="${plugin_version}"
         fragment="true"/>

</feature>
''')

BINARY_POM_TEMPLATE = Template('''<?xml version="1.0" encoding="UTF-8"?>
<project
    xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd"
    xmlns="http://maven.apache.org/POM/4.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.collins.trustedsystems.z3</groupId>
        <artifactId>com.collins.trustedsystems.z3.parent</artifactId>
        <version>${plugin_version}</version>
    </parent>
    <artifactId>${artifact_id}</artifactId>
    <packaging>eclipse-plugin</packaging>

    <build>
        <plugins>
            <!-- tycho is not able to automatically determine os/ws/arch of this bundle -->
            <plugin>
                <groupId>org.eclipse.tycho</groupId>
                <artifactId>target-platform-configuration</artifactId>
                <version>$${tycho.version}</version>
                <configuration>
                    <resolver>p2</resolver>
                    <environments>
                        <environment>
                            <os>${os}</os>
                            <ws>${ws}</ws>
                            <arch>${arch}</arch>
                        </environment>
                    </environments>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
''')

BINARY_MANIFEST_TEMPLATE = Template('''Manifest-Version: 1.0
Bundle-ManifestVersion: 2
Bundle-Name: Z3 Linux GTK x86_64 binaries
Bundle-SymbolicName: com.collins.trustedsystems.z3.${os}.${ws}.${arch};singleton:=true
Bundle-Version: ${plugin_version}
Bundle-Vendor: Collins Aerospace
Fragment-Host: com.collins.trustedsystems.z3;bundle-version="${plugin_version}"
Automatic-Module-Name: ${artifact_id}
Bundle-RequiredExecutionEnvironment: JavaSE-1.8
Eclipse-PlatformFilter: (& (osgi.os=${os}) (osgi.ws=${ws}) (osgi.arch=${arch}) )
''')

TARGET_POM_TEMPLATE = Template('''<project xmlns="http://maven.apache.org/POM/4.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>com.collins.trustedsystems.z3</groupId>
        <artifactId>com.collins.trustedsystems.z3.parent</artifactId>
        <version>${plugin_version}</version>
    </parent>
    <artifactId>com.collins.trustedsystems.z3.target</artifactId>
    <packaging>eclipse-target-definition</packaging>

</project>
''')

REPOSITORY_POM_TEMPLATE = Template('''<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>com.collins.trustedsystems.z3</groupId>
        <artifactId>com.collins.trustedsystems.z3.parent</artifactId>
        <version>${plugin_version}</version>
    </parent>
    <artifactId>com.collins.trustedsystems.z3.repository</artifactId>
    <packaging>eclipse-repository</packaging>

    <build>
        <plugins>
            <plugin>
                <groupId>org.eclipse.tycho.extras</groupId>
                <artifactId>tycho-p2-extras-plugin</artifactId>
                <version>$${tycho.version}</version>
                <executions>
                    <execution>
                        <phase>prepare-package</phase>
                        <goals>
                            <goal>mirror</goal>
                        </goals>
                    </execution>
                </executions>
                <configuration>
                    <destination>${project.build.directory}/repository</destination>
                    <source>
                        <repository>
                            <url>https://raw.githubusercontent.com/smaccm/z3-plugin-test/master/com.collins.trustedsystems.z3.repository/target/repository/</url>
                            <layout>p2</layout>
                            <!-- supported layouts are "p2-metadata", "p2-artifacts", and "p2" (for joint repositories; default) -->
                        </repository>
                    </source>
                </configuration>
            </plugin>
        </plugins>
        <pluginManagement>
            <plugins>
                <plugin>
                    <groupId>org.eclipse.m2e</groupId>
                    <artifactId>lifecycle-mapping</artifactId>
                    <version>1.0.0</version>
                    <configuration>
                        <lifecycleMappingMetadata>
                            <pluginExecutions>
                                <pluginExecution>
                                    <pluginExecutionFilter>
                                        <groupId>
                                            org.apache.maven.plugins
                                        </groupId>
                                        <artifactId>
                                            maven-clean-plugin
                                        </artifactId>
                                        <versionRange>
                                            [2.5,)
                                        </versionRange>
                                        <goals>
                                            <goal>clean</goal>
                                        </goals>
                                    </pluginExecutionFilter>
                                    <action>
                                        <ignore></ignore>
                                    </action>
                                </pluginExecution>
                            </pluginExecutions>
                        </lifecycleMappingMetadata>
                    </configuration>
                </plugin>
            </plugins>
        </pluginManagement>
    </build>

    <dependencies>
    </dependencies>
</project>
''')

REPOSITORY_CATEGORY_TEMPLATE = Template('''<?xml version="1.0" encoding="UTF-8"?>
<site>
   <feature url="features/com.collins.trustedsystems.z3.feature_${plugin_version}.jar" id="com.collins.trustedsystems.z3.feature" version="${plugin_version}">
      <category name="main"/>
   </feature>
   <category-def name="main" label="Z3-Plugin"/>
</site>''')

__all__ = []
__version__ = 0.1
__date__ = '2019-03-29'
__updated__ = '2019-03-29'

BASE_PACKAGE = 'com.collins.trustedsystems.z3'
SOURCE_DIR = BASE_PACKAGE
FEATURE_DIR = '.'.join([BASE_PACKAGE, 'feature'])
LINUX_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'linux.gtk.x86_64'])
MACOS_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'macosx.cocoa.x86_64'])
WIN32_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'win32.win32.x86_64'])
REPO_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'repository'])
TARGET_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'target'])

DEBUG = 1

GITHUB_API = 'https://api.github.com/repos'
GITHUB_RELEASES = 'releases'

Z3_PROVER_OWNER = 'Z3Prover'
Z3_PROVER_REPO = 'z3'
Z3_PROVER_REQUEST = '/'.join([GITHUB_API, Z3_PROVER_OWNER, Z3_PROVER_REPO, GITHUB_RELEASES])

Z3_PLUGIN_OWNER = 'smaccm'
Z3_PLUGIN_REPO = 'z3-plugin-updates-test'
Z3_PLUGIN_REQUEST = '/'.join([GITHUB_API, Z3_PLUGIN_OWNER, Z3_PLUGIN_REPO, GITHUB_RELEASES])

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

def package_plugin(plugin_version, z3_version, z3_releases):
    '''Package a plugin from the exectuables for the corresponding release'''

    def get_binary_filename(release_binary_urls, substr):
        binary_filename = None
        filename_iter = filter(lambda n: substr in n, release_binary_urls.keys())
        for binary_filename in filename_iter:
            pass
        return binary_filename

    def extract_binaries(binaries_dir, binary_filename):
        response = requests.get(release_binary_urls[binary_filename], stream=True)
        response.raise_for_status()
        zipfilename = os.path.join(binaries_dir, binary_filename)
        with open(zipfilename, 'wb') as handle:
            for block in response.iter_content(1024):
                handle.write(block)
        if not os.path.exists(binaries_dir):
            os.makedirs(binaries_dir)
        with ZipFile(zipfilename) as zipfile:
            contents = zipfile.infolist()
            zipfile.extractall(binaries_dir)
        if os.path.exists(zipfilename):
            os.remove(zipfilename)

    def get_deps_linux(rootdir):
        def get_deps_linux_rec(file):
            def call_ldd(file):
                import subprocess
                return subprocess.check_output(['ldd', file]).decode('ascii')
            pattern = re.compile(r'\s*(\S+)\s+=>\s+not found')
            dir_name = os.path.dirname(file)
            ldd_out = [str(x) for x in call_ldd(file).splitlines()]
            deps = {pattern.match(x).group(1) for x in ldd_out if 'not found' in x}
            trans_deps = set()
            for d in deps:
                trans_deps = trans_deps | get_deps_linux_rec(os.path.join(dir_name, d))
            return {file} | trans_deps | deps
        z3_exec = next(iter([os.path.join(d,f) for d,_,files in os.walk(rootdir) for f in files if f == 'z3']), None)
        return [x for x in get_deps_linux_rec(z3_exec)]

    def get_deps_osx(rootdir):
        mgraph = MachOGraph()
        z3_exec = None
        for folder, _, files in os.walk(rootdir):
            for file in files:
                fn = os.path.join(folder, file)
                if file == 'z3':
                    z3_exec = fn
                try:
                    mgraph.run_file(fn)
                except Exception:
                    pass
        return [x for x in filter(lambda d: rootdir in d, mgraph.graph.forw_bfs(z3_exec))]

    def get_deps_win32(rootdir):
        def get_casefold_namemap(rootdir):
            return {x.upper() : x for x in [os.path.join(d,f) for d,_,files in os.walk(rootdir) for f in files]}
        def get_deps_win32_rec(file):
            def call_objdump(file):
                import subprocess
                return subprocess.check_output(['objdump', '-p', file]).decode('ascii')
            pattern = re.compile(r'\s*DLL\s+Name:\s*(\S+)')
            dir_name = os.path.dirname(file)
            ldd_out = [str(x) for x in call_objdump(file).splitlines()]
            dll_list = [x for x in ldd_out if 'DLL' in x]
            raw_deps = {os.path.join(dir_name, x.group(1)) for x in [pattern.search(l) for l in dll_list] if x}
            deps = {casefold_map[d.upper()] for d in raw_deps if d.upper() in casefold_map}
            trans_deps = set()
            for d in deps:
                trans_deps = trans_deps | get_deps_win32_rec(d)
            return {file} | trans_deps | deps
        casefold_map = get_casefold_namemap(rootdir)
        z3_exec = next(iter([os.path.join(d,f) for d,_,files in os.walk(rootdir) for f in files if f == 'z3.exe']), None)
        return [x for x in get_deps_win32_rec(z3_exec)]

    release_description = next(filter(lambda desc: desc['tag_name'] == z3_version, z3_releases), None)
    if release_description:
        print('Building plugin version %s for Z3 version %s...' % (plugin_version,z3_version))

        gitrepo = Repo(os.getcwd())

        release_binary_urls = {x['name'] : x['browser_download_url'] for x in release_description['assets']}

        with open('pom.xml', 'w') as text_file:
            text_file.write(POM_TEMPLATE.safe_substitute(plugin_version = plugin_version))

        with open(os.path.join(SOURCE_DIR, 'pom.xml'), 'w') as text_file:
            text_file.write(SOURCE_POM_TEMPLATE.safe_substitute(plugin_version = plugin_version))

        with open(os.path.join(SOURCE_DIR, 'META-INF', 'MANIFEST.MF'), 'w') as text_file:
            text_file.write(SOURCE_MANIFEST_TEMPLATE.safe_substitute(plugin_version=plugin_version))

        with open(os.path.join(FEATURE_DIR, 'pom.xml'), 'w') as text_file:
            text_file.write(FEATURE_POM_TEMPLATE.safe_substitute(plugin_version = plugin_version))

        with open(os.path.join(FEATURE_DIR, 'feature.xml'), 'w') as text_file:
            text_file.write(FEATURE_XML_TEMPLATE.safe_substitute(plugin_version = plugin_version))

        with open(os.path.join(LINUX_PACKAGE_DIR, 'pom.xml'), 'w') as text_file:
            text_file.write(BINARY_POM_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=LINUX_PACKAGE_DIR, os='linux', ws='gtk', arch='x86_64'))

        with open(os.path.join(LINUX_PACKAGE_DIR, 'META-INF', 'MANIFEST.MF'), 'w') as text_file:
            text_file.write(BINARY_MANIFEST_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=LINUX_PACKAGE_DIR, os='linux', ws='gtk', arch='x86_64'))

        # Download and unpack binaries into binaries dir
        with tempfile.TemporaryDirectory() as temp_dir:
            binaries_dir = os.path.join(LINUX_PACKAGE_DIR, 'binaries')
            binary_filename = get_binary_filename(release_binary_urls, 'x64-ubuntu')
            try:
                gitrepo.git.rm('-r', binaries_dir)
            except Exception as e:
                sys.stderr.write(str(e))
            extract_binaries(temp_dir, binary_filename)
            z3_deps = get_deps_linux(temp_dir)
            if not os.path.exists(binaries_dir):
                os.makedirs(binaries_dir)
            for dep in z3_deps:
                copyfile(dep, os.path.join(binaries_dir, os.path.basename(dep)))
            gitrepo.git.add(binaries_dir)

        with open(os.path.join(MACOS_PACKAGE_DIR, 'pom.xml'), 'w') as text_file:
            text_file.write(BINARY_POM_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=MACOS_PACKAGE_DIR, os='macosx', ws='cocoa', arch='x86_64'))

        with open(os.path.join(MACOS_PACKAGE_DIR, 'META-INF', 'MANIFEST.MF'), 'w') as text_file:
            text_file.write(BINARY_MANIFEST_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=MACOS_PACKAGE_DIR, os='macosx', ws='cocoa', arch='x86_64'))

        # Download and unpack binaries into binaries dir
        with tempfile.TemporaryDirectory() as temp_dir:
            binaries_dir = os.path.join(MACOS_PACKAGE_DIR, 'binaries')
            binary_filename = get_binary_filename(release_binary_urls, 'x64-osx')
            try:
                gitrepo.git.rm('-r', binaries_dir)
            except Exception as e:
                sys.stderr.write(str(e))
            extract_binaries(temp_dir, binary_filename)
            z3_deps = get_deps_osx(temp_dir)
            if not os.path.exists(binaries_dir):
                os.makedirs(binaries_dir)
            for dep in z3_deps:
                copyfile(dep, os.path.join(binaries_dir, os.path.basename(dep)))
            gitrepo.git.add(binaries_dir)

        with open(os.path.join(WIN32_PACKAGE_DIR, 'pom.xml'), 'w') as text_file:
            text_file.write(BINARY_POM_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=WIN32_PACKAGE_DIR, os='win32', ws='win32', arch='x86_64'))

        with open(os.path.join(WIN32_PACKAGE_DIR, 'META-INF', 'MANIFEST.MF'), 'w') as text_file:
            text_file.write(BINARY_MANIFEST_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=WIN32_PACKAGE_DIR, os='win32', ws='win32', arch='x86_64'))

        # Download and unpack binaries into binaries dir
        with tempfile.TemporaryDirectory() as temp_dir:
            binaries_dir = os.path.join(WIN32_PACKAGE_DIR, 'binaries')
            binary_filename = get_binary_filename(release_binary_urls, 'x64-win')
            try:
                gitrepo.git.rm('-r', binaries_dir)
            except Exception as e:
                sys.stderr.write(str(e))
            extract_binaries(temp_dir, binary_filename)
            z3_deps = get_deps_win32(temp_dir)
            if not os.path.exists(binaries_dir):
                os.makedirs(binaries_dir)
            for dep in z3_deps:
                copyfile(dep, os.path.join(binaries_dir, os.path.basename(dep)))
            gitrepo.git.add(binaries_dir)

        with open(os.path.join(TARGET_PACKAGE_DIR, 'pom.xml'), 'w') as text_file:
            text_file.write(TARGET_POM_TEMPLATE.safe_substitute(plugin_version = plugin_version))

        with open(os.path.join(REPO_PACKAGE_DIR, 'pom.xml'), 'w') as text_file:
            text_file.write(REPOSITORY_POM_TEMPLATE.safe_substitute(plugin_version=plugin_version))

        with open(os.path.join(REPO_PACKAGE_DIR, 'category.xml'), 'w') as text_file:
            text_file.write(REPOSITORY_CATEGORY_TEMPLATE.safe_substitute(plugin_version=plugin_version))

        # Launch maven to build repository
        subprocess.call(['mvn', 'clean', 'verify'])

        # Commit/push this repository
        gitrepo.git.add('-A')
        gitrepo.git.commit('-m', 'Package plugin version %s' % (plugin_version))
        gitrepo.git.tag(plugin_version)
        gitrepo.git.push()
        gitrepo.git.push('--tags')

    else:
        sys.stderr.write('Cannot find release description for %s' % (z3_version))

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Copyright 2019 Collins Aerospace. All rights reserved.

  MIT License
  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the ""Software""), to
  deal in the Software without restriction, including without limitation the
  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
  sell copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:
  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.
  THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.
''' % (program_shortdesc)

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]")
        parser.add_argument("-i", "--include", dest="include", help="only include releasess matching this regex pattern. Note: exclude is given preference over include. [default: %(default)s]", metavar="RE" )
        parser.add_argument("-e", "--exclude", dest="exclude", help="exclude paths matching this regex pattern. [default: %(default)s]", metavar="RE" )
        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        # Process arguments
        args = parser.parse_args()

        verbose = args.verbose
        inpattern = args.include
        expattern = args.exclude

        if verbose > 0:
            print("Verbose mode on")

        if inpattern and expattern and inpattern == expattern:
            raise CLIError("include and exclude pattern are equal! Nothing will be processed.")

        z3_response = requests.get(Z3_PROVER_REQUEST)
        z3_releases = z3_response.json()
        z3_versions = [rel['tag_name'] for rel in z3_releases]

        #extant_plugin_releases = requests.get(Z3_PLUGIN_REQUEST).json()
        #extant_plugin_versions = [rel['tag_name'] for rel in extant_plugin_releases]
        extant_plugin_versions = ['4.7.1']

        # filter out the versions matching the exclude pattern
        if expattern:
            regex = re.compile(expattern)
            z3_versions = [x for x in filter(lambda x: not regex.match(x), z3_versions)]

        # filter on include pattern
        if inpattern:
            regex = re.compile(inpattern)
            z3_versions = [x for x in filter(regex.match, z3_versions)]

        # Find the plugin version corresponding to the z3-version
        regex = re.compile(r'\d+\.\d+\.\d+')
        plugin_versions = {regex.search(x).group(0) : x for x in filter(regex.search, z3_versions)}

        # remove the versions already packaged as plugin
        plugin_versions = {v : plugin_versions[v] for v in filter(lambda x: (not x in extant_plugin_versions), plugin_versions)}

        build_order = sorted(plugin_versions.keys())

        for ver in build_order:
            package_plugin(ver, plugin_versions[ver], z3_releases)

        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    sys.exit(main())
