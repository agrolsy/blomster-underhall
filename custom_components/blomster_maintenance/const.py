DOMAIN = "blomster_maintenance"
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.data"

CONF_WATER_SOURCE_ENTITY = "water_source_entity"
CONF_WATER_INSTALLATION_DATE = "water_installation_date"
CONF_BLADE_USAGE_ENTITY = "blade_usage_entity"
CONF_BLADE_WARNING_ENTITY = "blade_warning_entity"
CONF_BLADE_INTERVAL_HOURS = "blade_interval_hours"
DEFAULT_BLADE_INTERVAL_HOURS = 150.0

SERVICE_SET_WATER_BASELINE = "set_water_baseline"
SERVICE_RECORD_MAINTENANCE = "record_maintenance"
SERVICE_DELETE_MAINTENANCE = "delete_maintenance"

ATTR_BASELINE_LITERS = "baseline_liters"
ATTR_ITEM_ID = "item_id"
ATTR_EVENT_ID = "event_id"
ATTR_NAME = "name"
ATTR_NOTE = "note"
ATTR_METER_ENTITY = "meter_entity"

WATER_SENSOR_UNIQUE_ID = f"{DOMAIN}_water_total"
BLADE_REMAINING_SENSOR_UNIQUE_ID = f"{DOMAIN}_blade_remaining"
BLADE_DUE_BINARY_SENSOR_UNIQUE_ID = f"{DOMAIN}_blade_due"
EVENT_WATER_UPDATED = f"{DOMAIN}_water_updated"
EVENT_MAINTENANCE_UPDATED = f"{DOMAIN}_maintenance_updated"
