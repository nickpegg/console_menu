# Console Menu

Simple menu-driven program for consoling into servers connected via
/dev/ttyUSB\*. This is useful when you're building a little console server and
it's not really deterministic which hosts are plugged into which ports, like if
you're using USB-to-RS232 adapter cables.

## Installation
1. `git clone` this repo
2. `pipenv install`

## Usage
Basic usage: `./console_menu`

When given a hostname via command-line, e.g. `./console_menu <hostname>`, it
will connect you directly to that hostname. Otherwise, it will detect present
you with a menu of hosts it was able to detect.

Detection is done by looking for a Linux login prompt: `<hostname> login:`
