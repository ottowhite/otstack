{pkgs ? import <nixpkgs> {}}:

pkgs.mkShell {
	buildInputs = with pkgs; [
		uv
	];

	shellHook = ''
	unset PYTHONPATH
	unset PYTHONHOME
	unset PYTHONNOUSERSITE
	uv sync --all-extras
	git config core.hooksPath .githooks
	uv pip install --editable .
	'';
}
