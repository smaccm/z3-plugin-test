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
import subprocess
import sys
import tempfile

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from git import Repo
from github3 import GitHub
from macholib.MachOGraph import MachOGraph
from pprint import pprint, pformat
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
        <module>com.collins.trustedsystems.z3.updates</module>
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

UPDATES_POM_TEMPLATE = Template('''<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>com.collins.trustedsystems.z3</groupId>
        <artifactId>com.collins.trustedsystems.z3.parent</artifactId>
        <version>${plugin_version}</version>
    </parent>
    <artifactId>com.collins.trustedsystems.z3.updates</artifactId>
    <packaging>eclipse-repository</packaging>

    <build>
        <plugins>
            <plugin>
                <artifactId>maven-antrun-plugin</artifactId>
                <version>1.4</version>
                <executions>
                    <execution>
                        <id>save-previous-repository</id>
                        <phase>pre-clean</phase>
                        <configuration>
                            <tasks>
                                <copy todir="${project.basedir}/prev-repository">
                                    <fileset dir="${project.build.directory}/repository"
                                        includes="**/*" />
                                </copy>
                            </tasks>
                        </configuration>
                        <goals>
                            <goal>run</goal>
                        </goals>
                    </execution>
                    <execution>
                        <id>restore-repository</id>
                        <phase>prepare-package</phase>
                        <configuration>
                            <tasks>
                                <mkdir dir="${project.build.directory}/repository"/>
                                <copy todir="${project.build.directory}/repository">
                                    <fileset dir="${project.basedir}/prev-repository"
                                        includes="**/*" />
                                </copy>
                            </tasks>
                        </configuration>
                        <goals>
                            <goal>run</goal>
                        </goals>
                    </execution>
                    <execution>
                        <id>remove-prev-repository</id>
                        <phase>prepare-package</phase>
                        <configuration>
                            <tasks>
                                <delete includeEmptyDirs="true">
                                    <fileset dir="${project.basedir}/prev-repository" />
                                </delete>
                            </tasks>
                        </configuration>
                        <goals>
                            <goal>run</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
            <plugin>
                <groupId>org.eclipse.tycho</groupId>
                <artifactId>tycho-p2-repository-plugin</artifactId>
                <version>${tycho.version}</version>
                <configuration>
                    <skipArchive>true</skipArchive>
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

UPDATES_CATEGORY_TEMPLATE = Template('''<?xml version="1.0" encoding="UTF-8"?>
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

AUTH_TOKEN = os.environ['GH_TOKEN'] if 'GH_TOKEN' in os.environ.keys() else None

BASE_PACKAGE = 'com.collins.trustedsystems.z3'
SOURCE_DIR = BASE_PACKAGE
FEATURE_DIR = '.'.join([BASE_PACKAGE, 'feature'])
LINUX_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'linux.gtk.x86_64'])
MACOS_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'macosx.cocoa.x86_64'])
WIN32_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'win32.win32.x86_64'])
REPO_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'repository'])
UPDATES_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'updates'])
TARGET_PACKAGE_DIR = '.'.join([BASE_PACKAGE, 'target'])

DEBUG = 1

GITHUB_API = 'https://api.github.com/repos'
GITHUB_RELEASES = 'releases'

Z3_PROVER_OWNER = 'Z3Prover'
Z3_PROVER_REPO = 'z3'
Z3_PROVER_REQUEST = '/'.join([GITHUB_API, Z3_PROVER_OWNER, Z3_PROVER_REPO, GITHUB_RELEASES])

Z3_PLUGIN_OWNER = 'smaccm'
Z3_PLUGIN_REPO = 'z3-plugin-test'
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

    def get_asset(release_assets_by_name, substr):
        asset = None
        filename_iter = filter(lambda n: substr in n, release_assets_by_name.keys())
        for asset in filename_iter:
            pass
        return release_assets_by_name[asset]

    def extract_binaries(binaries_dir, asset):
        print('  Downloading binary package %s ...' % (asset.name))
        zipfilename = asset.download(os.path.join(binaries_dir, asset.name))
        print('  Download complete.  Extracting...')
        if not os.path.exists(binaries_dir):
            os.makedirs(binaries_dir)
        with ZipFile(zipfilename) as zipfile:
            contents = zipfile.infolist()
            zipfile.extractall(binaries_dir)
        print('  Extraction complete.')
        if os.path.exists(zipfilename):
            os.remove(zipfilename)
        print('  Downloaded file removed.')

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

    release_description = next(filter(lambda r: r.tag_name == z3_version, z3_releases), None)
    if release_description:
        print('Building plugin version %s for Z3 version %s...' % (plugin_version,z3_version))

        gitrepo = Repo(os.getcwd())

        # Since we're in detached head state, make a branch on which to work
        try:
            print('  Creating branch for building %s...' % (plugin_version))
            git_result = gitrepo.git.branch('-b', plugin_version, with_extended_output=True)
            print(git_result[1])
            if (git_result[0] != 0) :
                sys.stderr.write(git_result[2])
                sys.exit(git_result[0])
        except Exception as e:
             sys.stderr.write(str(e))
             sys.exit(1)

        release_assets_by_name = {x.name : x for x in release_description.assets()}

        filename = 'pom.xml'
        with open(filename, 'w') as text_file:
            text_file.write(POM_TEMPLATE.safe_substitute(plugin_version = plugin_version))
        print('  Generated %s.' % (filename))

        filename = os.path.join(SOURCE_DIR, 'pom.xml')
        with open(filename, 'w') as text_file:
            text_file.write(SOURCE_POM_TEMPLATE.safe_substitute(plugin_version = plugin_version))
        print('  Generated %s.' % (filename))

        filename = os.path.join(SOURCE_DIR, 'META-INF', 'MANIFEST.MF')
        with open(filename, 'w') as text_file:
            text_file.write(SOURCE_MANIFEST_TEMPLATE.safe_substitute(plugin_version=plugin_version))
        print('  Generated %s.' % (filename))

        filename = os.path.join(FEATURE_DIR, 'pom.xml')
        with open(filename, 'w') as text_file:
            text_file.write(FEATURE_POM_TEMPLATE.safe_substitute(plugin_version = plugin_version))
        print('  Generated %s.' % (filename))

        filename = os.path.join(FEATURE_DIR, 'feature.xml')
        with open(filename, 'w') as text_file:
            text_file.write(FEATURE_XML_TEMPLATE.safe_substitute(plugin_version = plugin_version))
        print('  Generated %s.' % (filename))

        filename = os.path.join(LINUX_PACKAGE_DIR, 'pom.xml')
        with open(filename, 'w') as text_file:
            text_file.write(BINARY_POM_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=LINUX_PACKAGE_DIR, os='linux', ws='gtk', arch='x86_64'))
        print('  Generated %s.' % (filename))

        filename = os.path.join(LINUX_PACKAGE_DIR, 'META-INF', 'MANIFEST.MF')
        with open(filename, 'w') as text_file:
            text_file.write(BINARY_MANIFEST_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=LINUX_PACKAGE_DIR, os='linux', ws='gtk', arch='x86_64'))
        print('  Generated %s.' % (filename))

        # Download and unpack binaries into binaries dir
        with tempfile.TemporaryDirectory() as temp_dir:
            binaries_dir = os.path.join(LINUX_PACKAGE_DIR, 'binaries')
            asset = get_asset(release_assets_by_name, 'x64-ubuntu')
            try:
                removed_elements = gitrepo.index.remove([binaries_dir], True, r=True)
                print('  Previous binaries removed from git: %s' % (pformat(removed_elements)))
            except Exception as e:
                sys.stderr.write(str(e))
            extract_binaries(temp_dir, asset)
            z3_deps = get_deps_linux(temp_dir)
            print('  Required (deps) files: %s' % (pformat(z3_deps)))
            if not os.path.exists(binaries_dir):
                os.makedirs(binaries_dir)
            for dep in z3_deps:
                copyfile(dep, os.path.join(binaries_dir, os.path.basename(dep)))
            print('  Required files copied.')
            #added_elements = gitrepo.index.add([os.path.join(binaries_dir, os.path.basename(dep)) for dep in z3_deps])
            #print('  New binaries added to git: %s' % (added_elements))

        filename = os.path.join(MACOS_PACKAGE_DIR, 'pom.xml')
        with open(filename, 'w') as text_file:
            text_file.write(BINARY_POM_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=MACOS_PACKAGE_DIR, os='macosx', ws='cocoa', arch='x86_64'))
        print('  Generated %s.' % (filename))

        filename = os.path.join(MACOS_PACKAGE_DIR, 'META-INF', 'MANIFEST.MF')
        with open(filename, 'w') as text_file:
            text_file.write(BINARY_MANIFEST_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=MACOS_PACKAGE_DIR, os='macosx', ws='cocoa', arch='x86_64'))
        print('  Generated %s.' % (filename))

        # Download and unpack binaries into binaries dir
        with tempfile.TemporaryDirectory() as temp_dir:
            binaries_dir = os.path.join(MACOS_PACKAGE_DIR, 'binaries')
            asset = get_asset(release_assets_by_name, 'x64-osx')
            try:
                removed_elements = gitrepo.index.remove([binaries_dir], True, r=True)
                print('  Previous binaries removed from git: %s' % (pformat(removed_elements)))
            except Exception as e:
                sys.stderr.write(str(e))
            print('  Previous binaries directory removed from git.')
            extract_binaries(temp_dir, asset)
            z3_deps = get_deps_osx(temp_dir)
            print('  Required (deps) files: %s' % (pformat(z3_deps)))
            if not os.path.exists(binaries_dir):
                os.makedirs(binaries_dir)
            for dep in z3_deps:
                copyfile(dep, os.path.join(binaries_dir, os.path.basename(dep)))
            print('  Required files copied.')

        filename = os.path.join(WIN32_PACKAGE_DIR, 'pom.xml')
        with open(filename, 'w') as text_file:
            text_file.write(BINARY_POM_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=WIN32_PACKAGE_DIR, os='win32', ws='win32', arch='x86_64'))
        print('  Generated %s.' % (filename))

        filename = os.path.join(WIN32_PACKAGE_DIR, 'META-INF', 'MANIFEST.MF')
        with open(filename, 'w') as text_file:
            text_file.write(BINARY_MANIFEST_TEMPLATE.safe_substitute(plugin_version=plugin_version, artifact_id=WIN32_PACKAGE_DIR, os='win32', ws='win32', arch='x86_64'))
        print('  Generated %s.' % (filename))

        # Download and unpack binaries into binaries dir
        with tempfile.TemporaryDirectory() as temp_dir:
            binaries_dir = os.path.join(WIN32_PACKAGE_DIR, 'binaries')
            asset = get_asset(release_assets_by_name, 'x64-win')
            try:
                removed_elements = gitrepo.index.remove([binaries_dir], True, r=True)
                print('  Previous binaries removed from git: %s' % (pformat(removed_elements)))
            except Exception as e:
                sys.stderr.write(str(e))
            print('  Previous binaries directory removed from git.')
            extract_binaries(temp_dir, asset)
            z3_deps = get_deps_win32(temp_dir)
            print('  Required (deps) files: %s' % (pformat(z3_deps)))
            if not os.path.exists(binaries_dir):
                os.makedirs(binaries_dir)
            for dep in z3_deps:
                copyfile(dep, os.path.join(binaries_dir, os.path.basename(dep)))
            print('  Required files copied.')

        filename = os.path.join(TARGET_PACKAGE_DIR, 'pom.xml')
        with open(filename, 'w') as text_file:
            text_file.write(TARGET_POM_TEMPLATE.safe_substitute(plugin_version = plugin_version))
        print('  Generated %s.' % (filename))

        filename = os.path.join(REPO_PACKAGE_DIR, 'pom.xml')
        with open(filename, 'w') as text_file:
            text_file.write(REPOSITORY_POM_TEMPLATE.safe_substitute(plugin_version=plugin_version))
        print('  Generated %s.' % (filename))

        filename = os.path.join(REPO_PACKAGE_DIR, 'category.xml')
        with open(filename, 'w') as text_file:
            text_file.write(REPOSITORY_CATEGORY_TEMPLATE.safe_substitute(plugin_version=plugin_version))
        print('  Generated %s.' % (filename))

        filename = os.path.join(UPDATES_PACKAGE_DIR, 'pom.xml')
        with open(filename, 'w') as text_file:
            text_file.write(UPDATES_POM_TEMPLATE.safe_substitute(plugin_version=plugin_version))
        print('  Generated %s.' % (filename))

        filename = os.path.join(UPDATES_PACKAGE_DIR, 'category.xml')
        with open(filename, 'w') as text_file:
            text_file.write(UPDATES_CATEGORY_TEMPLATE.safe_substitute(plugin_version=plugin_version))
        print('  Generated %s.' % (filename))

        # Launch maven to build repository
        subprocess.call(['mvn', 'clean', 'verify'])

        # Commit/push this repository
        try:
            print('  Adding objects to git index...')
            git_result = gitrepo.git.add('-A', with_extended_output=True)
            print(git_result[1])
            if (git_result[0] != 0) :
                sys.stderr.write(git_result[2])
                sys.exit(git_result[0])
            print('  Calling git commit...')
            git_result = gitrepo.git.commit('-m', 'Package plugin version %s' % (plugin_version), with_extended_output=True)
            print(git_result[1])
            if (git_result[0] != 0) :
                sys.stderr.write(git_result[2])
                sys.exit(git_result[0])
            print('  Calling git checkout master...')
            git_result = gitrepo.git.checkout('master', with_extended_output=True)
            print(git_result[1])
            if (git_result[0] != 0) :
                sys.stderr.write(git_result[2])
                sys.exit(git_result[0])
            print('  Calling git merge %s...' % (plugin_version))
            git_result = gitrepo.git.merge(plugin_version, with_extended_output=True)
            print(git_result[1])
            if (git_result[0] != 0) :
                sys.stderr.write(git_result[2])
                sys.exit(git_result[0])
            print('  Calling git tag...')
            tag_ref = gitrepo.git.tag(plugin_version, with_extended_output=True)
            print(git_result[1])
            if (git_result[0] != 0) :
                sys.stderr.write(git_result[2])
                sys.exit(git_result[0])
            print('  Calling git push...')
            gir_result = gitrepo.git.push('--quiet', '--set-upstream', 'origin-with-token', 'master', with_extended_output=True)
            print(git_result[1])
            if (git_result[0] != 0) :
                sys.stderr.write(git_result[2])
                sys.exit(git_result[0])
            print('  Calling git push tags...')
            git_result = gitrepo.git.push('origin-with-token', '--tags', with_extended_output=True)
            print(git_result[1])
            if (git_result[0] != 0) :
                sys.stderr.write(git_result[2])
                sys.exit(git_result[0])
            print('  Git update and push complete.')
        except Exception as e:
             sys.stderr.write(str(e))
             sys.exit(1)

    else:
        sys.stderr.write('Cannot find release description for %s' % (z3_version))

def release_plugin(plugin_version):
    gh = GitHub(GITHUB_API, token=AUTH_TOKEN)
    repository = gh.repository(Z3_PLUGIN_OWNER, Z3_PLUGIN_REPO)
    release = repository.create_release(plugin_version,
        target_commitish='master',
        name='Z3 Plugin %s' % (plugin_version),
        body='Eclipse plugin containing binaries for Z3 Prover version %s.' % (plugin_version),
        draft=False,
        prerelease=False,
    )
    filename = '%s-%s.zip' % (REPO_PACKAGE_DIR, plugin_version)
    filepath = os.path.join(REPO_PACKAGE_DIR, 'target', filename)
    asset = release.upload_asset(content_type='application/binary', name=filename, asset=open(filepath, 'rb'))

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

        if verbose and verbose > 0:
            print('Verbose mode on')

        if AUTH_TOKEN:
            print('Using Auth token string ending %s' % (AUTH_TOKEN[-4:]))
        else:
            print('No AUTH_TOKEN, using unauthenticated access')

        if inpattern and expattern and inpattern == expattern:
            raise CLIError("include and exclude pattern are equal! Nothing will be processed.")

        gh = GitHub(GITHUB_API, token=AUTH_TOKEN)
        prover_repository = gh.repository(Z3_PROVER_OWNER, Z3_PROVER_REPO)
        z3_releases = [r for r in prover_repository.releases()]
        z3_versions = [r.tag_name for r in z3_releases]

        plugin_repository = gh.repository(Z3_PLUGIN_OWNER, Z3_PLUGIN_REPO)
        extant_plugin_versions = [r.tag_name for r in plugin_repository.releases()]

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
        print('Building plugin versions: %s' % (pformat(build_order)))

        for ver in build_order:
            print('Building plugin version %s ...' % (ver))
            package_plugin(ver, plugin_versions[ver], z3_releases)
            release_plugin(ver)

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
