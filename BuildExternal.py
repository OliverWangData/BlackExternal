import argparse
import platform
import os
import re
import subprocess
import importlib.util
import shutil
import sys
import stat
import yaml
import datetime
import xml.etree.ElementTree as ET

def main():
    # Initializes the clargs and config.ini vars
    args = parse_args()
    with open(os.path.join(build_root, "BuildConfig.yaml")) as f: build_config = yaml.safe_load(f)
    
    # Ensures correct cmake version on build machine
    ensure_cmake_version(build_config["general"]["cmake_version"])
    
    # Keeps paths for CMAKE_PREFIX_PATH, to allow dependencies to find each other during build
    install_paths = []
    
    # Collect metadata to output to BuildMetadata file (Used by the module's build.cs)
    metadata = {}
    
    # Loop through each section in the .ini, which represents the library
    for library, versions in build_config.items():
    
        # Ignore general section
        if library == "general": continue
        
        # Adds the library to metadata
        if library not in metadata: metadata[library] = {}
        
        # Loop through versions
        for version, version_config in versions.items():

            # Ensure version exists
            if (version == ""):
                log(f"Version needs to be specified for '{library}'", True)
                continue;
                
            # Ensure the version's build type is actually valid input
            allowed_types = {"header", "static", "dynamic"}
            version_type = version_config.get("type", "header")
            
            if version_type not in allowed_types:
                log(f"Version type '{version_type}' is not valid", True)
                continue;
            
            # Ensure source path for library and version exist
            path_src = os.path.join(build_root, "External", library, version)
            
            if not os.path.exists(path_src): 
                log(f"Could not find '{library}/{version}'", True)
                continue
            
            # Metadata
            if version not in metadata[library]: metadata[library][version] = {}
            
            # Public definitions metadata
            definitions = version_config.get("public_definitions", [])
            if definitions: metadata[library][version]["public_definitions"] = definitions
            
            # Header only libraries only require syncing headers from the source code
            if version_type == "header": 
            
                log(f"Syncing headers for '{library}-{version}'\n", spaced = True)
            
                # Syncs includes from Install directory to Headers directory
                sync_directory(
                    os.path.join(path_src, version_config.get("include_source_folder", "include")), 
                    os.path.join(build_root, "Headers", library + "-" + version)
                    )
                
                continue
            
            # ==========================================================================================
            # Setup CMake configs
            
            # Configure, Build, and Install for each configuration
            for build_type in args.configs:
                
                # CMake platforms
                cmake_options = [
                    "-G", platform_configs[args.platform]["generators"],
                    "-A", platform_configs[args.platform]["arch"],
                    "-DCMAKE_BUILD_TYPE=" + build_type,
                    ]
                
                # CMake build type
                cmake_options.append("-DBUILD_SHARED_LIBS=" + ("OFF" if version_type == "static" else "ON"))
                
                # CMake paths
                path_install = os.path.join(
                    build_root, "Installs", 
                    library + "-" + version, 
                    args.platform, build_type
                    )
                cmake_options.append("-DCMAKE_PREFIX_PATH=" + ";".join(install_paths))
                cmake_options.append("-DCMAKE_INSTALL_PREFIX=" + path_install)
                install_paths.append(path_install)
                
                # Extra cmake flags
                cmake_flags = version_config.get("cmake_flags", {})
                cmake_options.extend(f"-D{key}={value}" for key, value in cmake_flags.items())
                
                # ======================================================================================
                # Configure, build, and install using CMake

                # Commands
                cmd_config = ["cmake", " ".join(cmake_options), "-B", path_install, path_src]
                cmd_build = ["cmake", "--build", path_install, "--config", build_type, "--verbose", "--parallel"]
                cmd_install = ["cmake", "--install", path_install, "--config", build_type]
                
                # Setting current working directory into the intermediates folder
                original_dir = os.getcwd()
                try:
                    # Clearing installs if required
                    if args.force:
                        # Changes read-only files on windows to read-write
                        def on_rm_error(func, path, exc_info):
                            os.chmod(path, stat.S_IWRITE)
                            os.unlink(path)
                            
                        if os.path.isdir(path_install): 
                            shutil.rmtree(path, onerror=on_rm_error)
                            
                    os.makedirs(path_install, exist_ok=True)
                    os.chdir(path_install)

                    # Configure
                    log(f"Configuring cmake for {library} for {build_type}\n", spaced = True)
                    log("Command: " + " ".join(cmd_config), spaced = True)
                    if os.system(" ".join(cmd_config)) != 0:
                        raise RuntimeError("CMake configure failed")

                    # Build
                    log(f"Building cmake for {library} for {build_type}\n", spaced = True)
                    log("Command: " + " ".join(cmd_build), spaced = True)
                    if os.system(" ".join(cmd_build)) != 0:
                        raise RuntimeError("CMake build failed")

                    # Install
                    log(f"Installing cmake for {library} for {build_type}\n", spaced = True)
                    log("Command: " + " ".join(cmd_install), spaced = True)
                    if os.system(" ".join(cmd_install)) != 0:
                        raise RuntimeError("CMake install failed")
                        
                    # Syncs includes from Install directory to Headers directory
                    sync_directory(
                        os.path.join(path_install, version_config.get("include_output_folder", "include")), 
                        os.path.join(build_root, "Headers", library + "-" + version)
                        )

                finally:
                    os.chdir(original_dir)
       
    # Write out BuildMetadata file
    xml_path = os.path.join(build_root, "BuildMetadata.xml")
    root = ET.Element("BuildMetadata")

    for library, versions in metadata.items():
        lib_elem = ET.SubElement(root, "Library", {"name": library})
        
        for version, items in versions.items():
            ver_elem = ET.SubElement(lib_elem, "Version", {"number": version})
            
            # Write public_definitions if they exist
            if "public_definitions" in items:
                defs_elem = ET.SubElement(ver_elem, "PublicDefinitions")
                for definition in items["public_definitions"]:
                    ET.SubElement(defs_elem, "Definition").text = definition

    # Write XML to file with UTF-8 encoding and pretty printing
    tree = ET.ElementTree(root)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    
    log(f"Output metadata to BuildMetadata.xml")

def parse_args():
    parser = argparse.ArgumentParser(description="Build system input")

    parser.add_argument(
        "-p", "--platform", 
        dest="platform",
        type=str, 
        required=True, 
        choices=platform_configs.keys(),
        help=f"Target platform, based on UTargetPlatform"
        )

    parser.add_argument(
        "-c", "--configs", 
        dest="configs",
        type=str, 
        nargs="+",
        required=False, 
        choices=build_configs,
        default=[build_configs[0]],
        help=f"One or more build configurations. Default: Release"
        )
        
    parser.add_argument(
        "-f", "--force",
        dest="force",
        action="store_true",
        help="Force a full rebuild of all libraries"
    )

    args = parser.parse_args()
    return args

# Accepts a version string
def ensure_cmake_version(version: str):

    # Try to find cmake in PATH
    try:
        version_tuple = tuple(int(part) for part in version.split('.'))
        result = subprocess.run(["cmake", "--version"], capture_output=True, text=True, check=True)
        version_line = result.stdout.splitlines()[0]  # usually like: "cmake version 3.21.1"
        version_match = re.search(r"cmake version (\d+)\.(\d+)\.(\d+)", version_line)
        if not version_match:
            raise RuntimeError("Could not parse cmake version string")

        version = tuple(int(x) for x in version_match.groups())
        if version < version_tuple:
            raise RuntimeError(f"CMake version too old: {version}, need at least {version_tuple}")

        log(f"Found CMake version {version}")
        return

    except (subprocess.CalledProcessError, FileNotFoundError):
        log("CMake not found in PATH", True)
        raise RuntimeError("No suitable CMake found") 

def clear_path(path):
    # Changes read-only files on windows to read-write
    def on_rm_error(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        os.unlink(path)
        
    if os.path.isdir(path): shutil.rmtree(path, onerror=on_rm_error)


def sync_directory(src, dst):
    if not os.path.exists(src):
        if os.path.exists(dst): shutil.rmtree(dst)
        return
    
    # Create the destination directory
    os.makedirs(dst, exist_ok=True)
    
    # Delete files/folders in dst that are not in src
    for item in os.listdir(dst):
        dst_path = os.path.join(dst, item)
        src_path = os.path.join(src, item)
        if not os.path.exists(src_path):
            if os.path.isdir(dst_path): shutil.rmtree(dst_path)
            else: os.remove(dst_path)
    
    # Copy everything from src to dst
    for item in os.listdir(src):
        src_path = os.path.join(src, item)
        dst_path = os.path.join(dst, item)
        if os.path.isdir(src_path): shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else: shutil.copy2(src_path, dst_path)


def log(msg: str, error: bool = False, spaced: bool = False):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = "[BuildExternal]"
    
    color = "\033[91m" if error else "\033[92m"  # Red for errors, green for info
    level = "[ERROR]" if error else "[INFO]"
    formatted_msg = f"{color}[{timestamp}] {prefix} {level} {msg}\033[0m"

    if spaced: print("\n" + formatted_msg + "\n")
    else: print(formatted_msg)

build_root = os.path.dirname(os.path.abspath(__file__)) # Assumes this file is at the root

# Default platform configurations. Based on UTargetPlatform, which usually implies arch. 
platform_configs = {
    "Win64" : {
        "generators" : '"Visual Studio 17 2022"',
        "arch" : "x64"
        },

    "Linux" : {
        "generators" : '"Unix Makefiles"',
        "arch" : "x86_64"
        },

    "Mac": {
        "generators": '"Xcode"',
        "arch":       "x86_64",
    },
    "IOS": {
        "generators": '"Xcode"',
        "arch":       "arm64",
    }
}

# Default build configurations
build_configs = ["Release", "RelWithDebInfo", "Debug"]

if __name__ == "__main__":
    log("Running BuildExternal.py")
    main()
    log("External module builds complete.")
