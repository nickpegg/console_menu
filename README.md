# Console Menu

Simple menu-driven program for consoling into servers connected via /dev/ttyUSB\*.

When given a hostname via command-line, e.g. `./console_menu <hostname`, it will connect
you directly to that hostname. Otherwise, it will detect present you with a menu of
hosts it was able to detect.

Detection is done by looking for a Linux login prompt: `<hostname> login:`
