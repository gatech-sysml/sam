#!/bin/sh

tmux new-session -d -s "c-16--16-2" bash bin/models/coarse/crop16/16__16_2.sh
tmux new-session -d -s "c-16--16-6" bash bin/models/coarse/crop16/16__16_6.sh
tmux new-session -d -s "c-16--16-10" bash bin/models/coarse/crop16/16__16_10.sh
#tmux new-session -d -s "c-16--22-2" bash bin/models/coarse/crop16/16__22_2.sh
#tmux new-session -d -s "c-16--22-6" bash bin/models/coarse/crop16/16__22_6.sh
#tmux new-session -d -s "c-16--22-10" bash bin/models/coarse/crop16/16__22_10.sh
#tmux new-session -d -s "c-16--28-2" bash bin/models/coarse/crop16/16__28_2.sh
#tmux new-session -d -s "c-16--28-6" bash bin/models/coarse/crop16/16__28_6.sh
#tmux new-session -d -s "c-16--28-10" bash bin/models/coarse/crop16/16__28_10.sh