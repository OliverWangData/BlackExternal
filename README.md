# BlackExternal

BlackExternal is an Unreal Engine plugin and pipeline for managing and building third-party C++ libraries using CMake. It simplifies integration of external dependencies into UE projects by centralizing build configuration and output.

## Requirements

- [CMake](https://cmake.org/download/) must be available in your system `PATH`
- Python 3.11.8 or later (for running the build script)

## How to Build External Libraries

1. Clone this repository.
2. Add the source code of the desired third-party library into "External/{LibraryName}/{Version}/"
3. Update "buildconfig.yaml" with build instructions and configuration for the new library. See file for example. 
4. Run "python BuildExternal.py" with the desired output build parameters.

## Using in Your Unreal Project

To consume the built libraries in another module, inherit from BlackExternalModuleBase.Build.cs and declare the libraries you want to use. Example:

```
using UnrealBuildTool;

public class ExampleExternal : BlackExternalModuleBase
{
    public override string[] Libraries => new[]
    {
        "freetype-2.13.3",
        "harfbuzz-11.2.1",
        "msdfgen-1.12",
        "utf8proc-2.10.0",
        "fastcppcsvparser-master"
    };

    public ExampleExternal(ReadOnlyTargetRules Target) : base(Target)
    {
        Type = ModuleType.External;
    }
}
```

This will automatically link the appropriate headers and binaries from the plugin’s output folders.

## Third-Party Example Libraries

This project includes the following third-party example libraries, each under their respective open-source licenses:

- **utf8proc** (MIT License) — https://github.com/JuliaStrings/utf8proc  
- **msdfgen** (MIT License) — https://github.com/Chlumsky/msdfgen  
- **harfbuzz** (MIT License) — https://github.com/harfbuzz/harfbuzz  
- **freetype** (FreeType Project License / BSD-style) — https://www.freetype.org  
- **fastcppcsvparser** (MIT License) — https://github.com/ben-strasser/fast-cpp-csv-parser  

License files for each library are included in their respective directories to comply with their licensing requirements.

## License

Please refer to the individual license files included with each third-party library for specific terms and conditions.  
