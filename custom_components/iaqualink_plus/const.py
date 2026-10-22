"""Constants for iAquaLink Plus."""

from datetime import timedelta

DOMAIN = "iaqualink_plus"
CORE_DOMAIN = "iaqualink"

UPDATE_INTERVAL = timedelta(seconds=60)

CMD_GET_HOME = "get_home"
CMD_GET_SWC_CONFIG = "get_swc_config"
CMD_SET_SWC_CONFIG = "set_swc_config"
CMD_CONTROL_SWC_BOOST = "control_swc_boost"

BOOST_ACTIVE_STATES = ("on", "paused")
SWC_STATUSES = ["standby", "running", "boosting", "boostpaused", "offline", "unknown"]
