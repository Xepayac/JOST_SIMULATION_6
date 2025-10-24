{ pkgs, ... }: {
  channel = "stable-23.11";
  packages = [
    (pkgs.python311.withPackages (ps: [
      ps.flask
      ps.flask-sqlalchemy
      ps.pytest
    ]))
    pkgs.sqlite
    
  ];
}
