# Z3-Plugin

Packages the Microsoft Z3 solver binaries into an Eclipse Plugin for convenient
use in Eclipse-based analysis tools.

## Packaging

Presently all supported OS/architecture binaries are packaged into one plug in.
In future, we hope to have the time to separate these into individual bundles,
requiring installation only of the the binary to support the local machine
OS/Architecture.

The presently supported versions are:

- Microsoft Windows WIN32, 64-bit
- Microsoft Windows WIN32, 32-bit
- Linux GTK, 64-bit
- Apple Macintosh OSX, 64-bit

## Updating

When Microsoft releases another version of Z3, it is natural that updated
versions of this plugin.  This is done by downloading (or building) the various
binaies for the supported versions, inserting them in the appropriate
directories in the main plugin project, and updating the version numbers in the
MANIFESTMF, feature.xml and various pom.xml files for the projects.  These are:

- com.collins.trustedsystems.z3/pom.xml: line 11
- com.collins.trustedsystems.z3/META-INF/MANIFEST.MF: line 5
- com.collins.trustedsystems.z3.feature/pom.xml: line 11
- com.collins.trustedsystems.z3.feature/feature.xml: line 5
- com.collins.trustedsystems.z3.parent/pom.xml: line 5 and line 94
- com.collins.trustedsystems.z3.target/pom.xml: line 8

As this plugin is rarely likely to have SNAPSHOT builds and manual management
of the seven locations that the version numbers appear does not seem that
onerous, we have not yet started using a release workflow plugin such as
[Tycho Release Workflow](https://wiki.eclipse.org/Tycho/Release_Workflow) or
[unleash-maven-plugin](https://github.com/shillner/unleash-maven-plugin).
