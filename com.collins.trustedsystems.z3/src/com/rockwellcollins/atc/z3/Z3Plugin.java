package com.collins.trustedsystems.z3;

import java.io.File;
import java.net.URL;

import org.eclipse.core.runtime.FileLocator;
import org.eclipse.core.runtime.Platform;
import org.osgi.framework.Bundle;

public class Z3Plugin {

	public static String getZ3Directory() {
		Bundle bundle = Platform.getBundle("com.collins.trustedsystems.z3");
		String archDir = getArchDir();
		String exeName = getExecutableName();
		try {
			// Extract entire directory so DLLs are available on windows
			URL dirUrl = FileLocator.toFileURL(bundle.getEntry(archDir));
			File exe = new File(dirUrl.getPath(), exeName);
			exe.setExecutable(true);
			return exe.getParent();
		} catch (Exception e) {
			throw new IllegalArgumentException("Unable to extract z3 from plug-in", e);
		}
	}

	private static String getArchDir() {
		String name = System.getProperty("os.name").toLowerCase();
		String arch = System.getProperty("os.arch").toLowerCase();

		if (name.contains("win32")) {
			if (arch.contains("64")) {
				return "win32.x86_64";
			} else {
				return "win32.x86";
			}
		} else if (name.contains("mac os x")) {
			return "macosx.x86_64";
		} else if (arch.contains("64")) {
			return "linux.x86_64";
		} else {
			return "linux.x86";
		}
	}

	private static String getExecutableName() {
		boolean isWindows = System.getProperty("os.name").startsWith("Windows");
		return isWindows ? "z3.exe" : "z3";
	}

}
