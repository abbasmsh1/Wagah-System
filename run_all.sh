#!/bin/bash
# Start the Wagah System (mounted app) and the periodic backup job.
#
# The legacy standalone apps (custom.py, arrived.py, sim.py, bus.py, train.py,
# plane.py, admin.py, modify.py, delete.py) are deliberately NOT started here:
# they predate main.py, bypass its auth/CSRF/rate-limit stack, and delete.py
# exposes unauthenticated destructive endpoints. Run one manually only if you
# need a feature that has not been migrated to routers/ yet.

set -e

alembic upgrade head
python backup.py &
python main.py
