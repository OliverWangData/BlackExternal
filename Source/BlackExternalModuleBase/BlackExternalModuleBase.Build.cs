// Copyright (c) Black Megacorp. All Rights Reserved.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml.Linq;
using UnrealBuildTool;

public abstract class BlackExternalModuleBase : ModuleRules
{
    public abstract string[] Libraries { get; }

	public BlackExternalModuleBase(ReadOnlyTargetRules Target) : base(Target)
	{
        // Since inherited modules will only define the libraries used, we can allow them to
        // store stuff like utility helpers as well. So don't need to make them External.
        // Type = ModuleType.External;
        string projDir = Path.GetDirectoryName(Target.ProjectFile.FullName);
        string rootDir = Path.Combine(projDir, "Plugins", "BlackExternal");

        // Load the XML document from the given path
        XDocument metadata = XDocument.Load(Path.Combine(rootDir, "BuildMetadata.xml"));

        foreach (string library in Libraries)
        {
            // Header directory
            // Plugins/BlackThirdParty/Headers/{lib-version}/
            string headerDir = Path.Combine(
                rootDir, "Headers", library
            );

            // Adds header includes
            if (Directory.Exists(headerDir)) PublicIncludePaths.Add(headerDir);

            // Install directory
            // Plugins/BlackThirdParty/Installs/{lib-version}/{platform}/{buildconfig}/
            string installDir = Path.Combine(
                rootDir, "Installs", library, Target.Platform.ToString(),
                GetConfigName(Target.Configuration)
            );

            // Add static library files (.lib, .a)
            string libDir = Path.Combine(installDir, "lib");
            if (Directory.Exists(libDir))
            {
                string[] files = Directory.GetFiles(libDir, GetStaticExt(Target.Platform));
                PublicAdditionalLibraries.AddRange(files);
            }

            // Add dynamic library files (.dll, .so, etc)
            string binDir = Path.Combine(installDir, "bin");
            if (Directory.Exists(binDir))
            {
                string[] files = Directory.GetFiles(binDir, GetDynamicExt(Target.Platform));
                foreach (string f in files) RuntimeDependencies.Add(f, StagedFileType.NonUFS);
            }

            // Add public defintions from the metadata xml
            string[] parts = library.Split('-');
            if (parts.Length < 2) throw new ArgumentException("Library missing '-'");
            string libraryName = parts[0];
            string versionName = parts[1];

            var libElement = metadata.Root.Elements("Library")
                .FirstOrDefault(lib => string.Equals(
                    lib.Attribute("name")?.Value, libraryName, StringComparison.OrdinalIgnoreCase));

            if (libElement == null) continue;

            // Find <Version> with matching number
            var versionElement = libElement.Elements("Version")
                .FirstOrDefault(ver => string.Equals(
                    ver.Attribute("number")?.Value, versionName, StringComparison.OrdinalIgnoreCase));

            if (versionElement == null) continue;

            var publicDefsElement = versionElement.Element("PublicDefinitions");
            if (publicDefsElement != null)
            {
                foreach (var defElem in publicDefsElement.Elements("Definition"))
                {
                    string def = defElem.Value.Trim();
                    if (!string.IsNullOrEmpty(def))
                    {
                        PublicDefinitions.Add(def);
                    }
                }
            }

        }
    }

    // Returns the name of the CMake configuration build configuration using 
    public static string GetConfigName(UnrealTargetConfiguration configuration)
    {
        if (!_configNameMap.TryGetValue(configuration, out var entry))
            throw new KeyNotFoundException($"No mapping found for {configuration}");

        return entry;
    }

    private static readonly Dictionary<UnrealTargetConfiguration, string> _configNameMap = new()
    {
        {UnrealTargetConfiguration.Shipping, "Release" },
        {UnrealTargetConfiguration.Development, "Release" },
        {UnrealTargetConfiguration.Test, "Release" }, // or RelWithDebInfo
        {UnrealTargetConfiguration.Debug, "Release" },		// or Debug
        {UnrealTargetConfiguration.DebugGame, "Release" }	// or Debug
    };

    private static string GetStaticExt(UnrealTargetPlatform platform)
    {
        if (!_platformStaticExtMap.TryGetValue(platform, out var entry))
            throw new KeyNotFoundException($"No mapping found for {platform}");

        return entry;
    }

    private static readonly Dictionary<UnrealTargetPlatform, string> _platformStaticExtMap = new()
    {
        { UnrealTargetPlatform.Win64, "*.lib" },
        { UnrealTargetPlatform.Linux, "*.a" },
        { UnrealTargetPlatform.Mac, "*.a" },
        { UnrealTargetPlatform.IOS, "*.a" },
        { UnrealTargetPlatform.Android, "*.a" }
    };

    private static string GetDynamicExt(UnrealTargetPlatform platform)
    {
        if (!_platformDynamicExtMap.TryGetValue(platform, out var entry))
            throw new KeyNotFoundException($"No mapping found for {platform}");

        return entry;
    }

    private static readonly Dictionary<UnrealTargetPlatform, string> _platformDynamicExtMap = new()
    {
        { UnrealTargetPlatform.Win64, "*.dll" },
        { UnrealTargetPlatform.Linux, "*.so" },
        { UnrealTargetPlatform.Mac, "*.dylib" },
        { UnrealTargetPlatform.IOS, "*.dylib" },
        { UnrealTargetPlatform.Android, "*.so" }
    };
}
