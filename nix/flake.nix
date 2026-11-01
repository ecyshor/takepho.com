{
  description = "takepho.com landing page";
  inputs = { nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable"; };
  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          playwrightBrowsers = pkgs.playwright-driver.browsers;
        in {
          default = pkgs.mkShell {
            buildInputs = with pkgs; [
              python3
              python3Packages.playwright
              python3Packages.pillow
              curl
              playwright-driver.browsers
            ];
            shellHook = ''
              export PLAYWRIGHT_BROWSERS_PATH=${playwrightBrowsers}
              export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
            '';
          };
        });
    };
}
