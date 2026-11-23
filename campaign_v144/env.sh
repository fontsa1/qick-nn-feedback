# Settings shared by the campaign scripts. Set them in the environment, or edit the defaults here.
#   QICK_BOARD_A, QICK_BOARD_B  IP address of each board (no default; a script stops if a board it uses is unset)
#   QICK_TOP                    folder with OG_build_v1.44.bit and .hwh (default firmware_v1.44)
#   QICK_BANNER                 build timestamp the board must report, e.g. "Nov  7 19:57:07" (default: read from the .hwh)
#   PYTHON                      Python interpreter (default python)
PY="${PYTHON:-python}"
TOP="${QICK_TOP:-firmware_v1.44}"
hwh_banner() { grep -o 'TIMESTAMP="[^"]*"' "$1" | head -1 | sed -E 's/TIMESTAMP="[A-Za-z]+ ([A-Za-z]+ +[0-9]+ [0-9:]+) [0-9]+"/\1/'; }
BANNER="${QICK_BANNER:-$(hwh_banner "$TOP/OG_build_v1.44.hwh")}"
[ -n "$BANNER" ] || { echo "no build banner: set QICK_BANNER, or QICK_TOP to the folder with the .hwh"; exit 2; }
host_of() { case $1 in
  A) echo "${QICK_BOARD_A:?set QICK_BOARD_A to the IP address of board A}";;
  B) echo "${QICK_BOARD_B:?set QICK_BOARD_B to the IP address of board B}";;
  *) echo "board A or B" >&2; return 2;; esac; }
