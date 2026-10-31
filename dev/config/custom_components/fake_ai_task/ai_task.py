"""Fake AI task entity: returns plausible canned values for vehicle receipts."""

import datetime

from homeassistant.components.ai_task import (
    AITaskEntity,
    AITaskEntityFeature,
    GenDataTask,
    GenDataTaskResult,
)
from homeassistant.components.conversation import ChatLog


async def async_setup_entry(hass, entry, async_add_entities):
    """Add the entity."""
    async_add_entities([FakeAiTask(entry)])


class FakeAiTask(AITaskEntity):
    """Returns canned receipt data. NOT a real OCR - for trying out the UI only."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = AITaskEntityFeature.GENERATE_DATA | AITaskEntityFeature.SUPPORT_ATTACHMENTS

    def __init__(self, entry) -> None:
        """Initialize."""
        self._attr_unique_id = entry.entry_id

    async def _async_generate_data(self, task: GenDataTask, chat_log: ChatLog) -> GenDataTaskResult:
        fields = set(task.structure.schema) if task.structure else set()
        names = {getattr(key, "schema", key) for key in fields}
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        canned = {
            "date": yesterday,
            "liters": 41.2, "price_per_liter": 1.759, "total_cost": 72.47,
            "kwh": 38.4, "price_per_kwh": 0.329,
            "cost": 289.5, "odometer": 48650,
        }
        data = {k: v for k, v in canned.items() if k in names}
        if "cost" in names:  # service invoice
            data["odometer"] = 48000
        if "kwh" in names:  # charge receipt
            data["total_cost"] = 12.63
        return GenDataTaskResult(conversation_id=chat_log.conversation_id, data=data)
