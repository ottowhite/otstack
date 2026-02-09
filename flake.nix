{
  description = "OtStack - PR dependency stack management for GitHub";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      ...
    }:
    let
      inherit (nixpkgs) lib;

      # Load the uv workspace from the current directory
      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      # Create overlay from workspace
      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };

      # Systems to support
      systems = [
        "x86_64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      # Helper to generate outputs for each system
      forAllSystems = lib.genAttrs systems;

      # Create pkgs and pythonSet for each system
      mkPkgsFor = system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python313;

          pythonSet =
            (pkgs.callPackage pyproject-nix.build.packages {
              inherit python;
            }).overrideScope
              (
                lib.composeManyExtensions [
                  pyproject-build-systems.overlays.default
                  overlay
                ]
              );
        in
        { inherit pkgs pythonSet; };

    in
    {
      packages = forAllSystems (system:
        let
          inherit (mkPkgsFor system) pythonSet;
          venv = pythonSet.mkVirtualEnv "otstack-env" workspace.deps.default;
        in
        {
          default = venv;
        }
      );

      apps = forAllSystems (system:
        let
          inherit (mkPkgsFor system) pythonSet;
          venv = pythonSet.mkVirtualEnv "otstack-env" workspace.deps.default;
        in
        {
          default = {
            type = "app";
            program = "${venv}/bin/ots";
          };
        }
      );
    };
}
