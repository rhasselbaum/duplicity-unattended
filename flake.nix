{
  description = "Nix flake for duplicity-unattended backup solution";

  inputs = {
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, utils, duplicity-unattended-src, ... }:
    utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        packages = {
          duplicity-unattended = pkgs.stdenv.mkDerivation {
            pname = "duplicity-unattended";
            version = "git";

            src = duplicity-unattended-src;
            buildInputs = [
              (pkgs.python3.withPackages (p: with p; [ boto3 pyyaml ]))
              pkgs.duplicity
              pkgs.makeWrapper
            ];

            installPhase = ''
              mkdir -p $out/bin
              cp $src/duplicity-unattended $out/bin/duplicity-unattended.py
              chmod +x $out/bin/duplicity-unattended.py
              makeWrapper $out/bin/duplicity-unattended.py $out/bin/duplicity-unattended \
                --set PATH ${pkgs.duplicity}/bin
            '';

            meta = with pkgs.lib; {
              description = "Unattended backups based on Duplicity";
              homepage = "https://github.com/rhasselbaum/duplicity-unattended";
              license = licenses.mit;
            };
          };
        };

        defaultPackage = self.packages.${system}.duplicity-unattended;
      }
    );
}
