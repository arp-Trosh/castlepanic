CASTLE PANIC {VERSION} for Windows
===================================

The co-operative tower-defence board game in 3D, in your terminal. Goblins, orcs and trolls
march out of the forest; together, keep at least one of the six Towers standing until every
Monster is slain.

STARTING
  1. Extract the whole zip first (right-click > Extract All). Don't run it from inside the zip.
  2. Open the CastlePanic folder and double-click CastlePanic.exe.

  The first start takes 10-20 seconds ("First run compile, please wait..."): the 3D graphics
  are compiled for your PC once and kept in the folder, so later starts are quick.

  It needs Windows 10 or 11. Windows Terminal (the default on Windows 11, and free in the
  Microsoft Store for Windows 10) looks best. Make the window big (maximize it): 120x34 or more
  is comfortable, 70x20 the least it will draw in. Nothing to install; to uninstall, delete the
  folder (and %APPDATA%\castlepanic, where your settings are kept).

  About the exe: CastlePanic.exe is the official Python program from python.org, renamed. It is
  signed by the Python Software Foundation, so Windows should run it without a warning.

PLAYING
  Single Player: 1 seat is the solo game (a hand of 6, discard up to 2); 2-6 seats fill the
  others with computer players.
  Your turn goes a step at a time; the Order of play window (bottom right) shows where you are.
  N, Enter or the NEXT STEP button moves on.
    1-9 or click        choose a card; then a letter (or click) picks the Monster,
                        a number the Wall. Brick + Mortar: choose both.
    click a card twice  discard it (step 2), or answer "All Players Discard 1 Card"
    T, or click         trade (step 3): your card, then one of theirs in Defenders.
                        Offered a trade: Y accept, N decline.
    Esc                 cancel a choice; take back a trade offer nobody answers
    arrows, + / -, R    turn and zoom the camera, R resets it (the mouse wheel zooms too)
    H (or F1)           how to play
    M                   sound on/off
    Q (twice)           leave the game
  Everything the 3D shows is also written in the log on the right.

MULTIPLAYER
  One player picks Host Game (Left/Right: seats, B: bots fill empty seats) and tells the others
  the address shown in the lobby. The others pick Join Game and type it in. Everyone must be on
  the same network, or the host has to forward the port (5555 by default). Tab opens the chat.
  If a player leaves, a computer player takes over their seat.

  The first time you HOST, Windows Firewall asks whether to allow "Python" (that's this game)
  on networks: allow it on Private networks. Joining a game and single player never ask.

GRAPHICS
  The menu's Settings screen sets the characters, colours, frame rate, shadows and reflections
  (F2-F6 switch them anywhere); they are kept for next time. Shadows and reflections off is
  faster on a slow PC. The bottom line shows the frame rate achieved.
  In Windows Terminal the game uses its finest graphics automatically. In the classic console it
  uses a coarser set that works with any font; if you ever see boxes or question marks, choose
  other Characters in Settings.
  Your player name is your Windows user name; change it on the menu (Name), or set it for every
  game by opening a Command Prompt in the CastlePanic folder and running
      set CASTLEPANIC_NAME=YourName
      CastlePanic.exe

LICENSES
  Castle Panic is a board game by Justin De Witt, published by Fireside Games. This is a fan-made
  version for friends: every model, sound and line of code in it is original.
  The 3D graphics are drawn by unicode3d (https://github.com/arp-Trosh/unicode3d), which is free
  software under the GNU Lesser General Public License, version 3 or later. Its source and license
  texts (COPYING, COPYING.LESSER) are in Lib\site-packages\unicode3d and
  Lib\site-packages\unicode3d-*.dist-info\licenses; you may replace it with your own version.
  Python (python.org), numpy (numpy.org), Numba (numba.pydata.org), llvmlite and Pillow
  (python-pillow.org) come with their own licenses, in the same places. msvcp140.dll and
  vcomp140.dll are Microsoft's C++ and OpenMP runtimes, included as Microsoft's Visual C++
  Redistributable license allows.
