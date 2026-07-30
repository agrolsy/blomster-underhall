DOMAIN = "blomster_maintenance"
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.data"

CONF_WATER_SOURCE_ENTITY = "water_source_entity"
CONF_WATER_INSTALLATION_DATE = "water_installation_date"

SERVICE_SET_WATER_BASELINE = "set_water_baseline"
SERVICE_RECORD_MAINTENANCE = "record_maintenance"

ATTR_BASELINE_LITERS = "baseline_liters"
ATTR_ITEM_ID = "item_id"
ATTR_NAME = "name"
ATTR_NOTE = "note"

WATER_SENSOR_UNIQUE_ID = f"{DOMAIN}_water_total"
EVENT_WATER_UPDATED = f"{DOMAIN}_water_updated"
EVENT_MAINTENANCE_UPDATED = f"{DOMAIN}_maintenance_updated"
