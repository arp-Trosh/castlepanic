## Castle Panic {VERSION} (playtest)

The co-operative tower-defence board game in 3D, in your terminal: defend the six Towers against goblins, orcs,
trolls and their bosses, alone (the solo game, or with computer players) or with friends over your network.

This is a playtest release: please report anything odd, with what you were doing when it happened.

### Windows

1. Download **CastlePanic-{VERSION}-windows-x64.zip** below.
2. Extract the whole zip (right-click > Extract All).
3. Open the `CastlePanic` folder and double-click **CastlePanic.exe**.

Needs Windows 10 or 11; nothing to install. Windows Terminal (the default on Windows 11) looks best; maximize the
window. The first start takes up to a minute while the 3D graphics are compiled for your PC; later starts are quick.

`CastlePanic.exe` is the official `python.exe` from python.org's embeddable package, renamed and still signed by the
Python Software Foundation. The release contains no unsigned or packed executable, so Windows has nothing to warn you
about. The first time you **host** a multiplayer game, Windows Firewall asks to allow "Python": allow it on private
networks.

The included README.txt covers controls, multiplayer and graphics.

### Linux / macOS

From the source code (Python 3.10 or later):

```sh
git clone https://github.com/arp-Trosh/castlepanic
cd castlepanic
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 -m castlepanic
```
