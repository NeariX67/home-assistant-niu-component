"""Constants for the Niu integration."""

ACCOUNT_BASE_URL = "https://account-fk.niu.com"
LOGIN_URI = "/v3/api/oauth2/token"
API_BASE_URL = "https://app-api-fk.niu.com"
MOTOR_BATTERY_API_URI = "/v3/motor_data/battery_info"
MOTOR_INDEX_API_URI = "/v5/scooter/motor_data/index_info"
MOTOINFO_LIST_API_URI = "/v5/scooter/list"
MOTOINFO_ALL_API_URI = "/motoinfo/overallTally"
TRACK_LIST_API_URI = "/v5/track/list/v2"
CMD_API_URI = "/v5/cmd/creat"

CMD_ACC_ON = "acc_on"
CMD_ACC_OFF = "acc_off"
CMD_FORTIFICATION_ON = "fortification_on"
CMD_FORTIFICATION_OFF = "fortification_off"

DOMAIN = "niu"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCOOTER_ID = "scooter_id"
CONF_AUTH = "conf_auth"

DEFAULT_SCOOTER_ID = 0

# Newer Niu models (e.g. dual/triple swappable-battery scooters) can report
# up to three battery compartments in the battery_info API response.
BATTERY_COMPARTMENTS = ("A", "B", "C")
