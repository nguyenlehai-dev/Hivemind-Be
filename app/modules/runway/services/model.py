from app.modules.runway.schemas import ModelCatalogResponse, ModelItem

CATALOG: list[ModelItem] = [
    ModelItem(
        id="nano-banana-2",
        name="Nano Banana 2",
        vendor="google",
        media_types=["image"],
        capabilities=["text_to_image", "image_to_image"],
    ),
    ModelItem(
        id="seedream-5",
        name="Seedream 5.0",
        vendor="runway",
        media_types=["image"],
        capabilities=["text_to_image", "image_to_image"],
    ),
    ModelItem(
        id="gen-4",
        name="Gen-4",
        vendor="runway",
        media_types=["image", "video"],
        capabilities=["image_to_image", "text_to_video"],
    ),
    ModelItem(
        id="gen3a-turbo",
        name="Gen-3 Turbo",
        vendor="runway",
        media_types=["video"],
        capabilities=["image_to_video", "text_to_video"],
    ),
    ModelItem(
        id="musicgen",
        name="MusicGen",
        vendor="meta",
        media_types=["audio"],
        capabilities=["text_to_music"],
    ),
    ModelItem(
        id="elevenlabs-sfx",
        name="ElevenLabs SFX",
        vendor="elevenlabs",
        media_types=["audio"],
        capabilities=["text_to_sfx"],
    ),
]


class ModelService:
    def __init__(self, catalog: list[ModelItem] | None = None) -> None:
        self._catalog = catalog if catalog is not None else CATALOG

    def get_models(self, mode: str) -> ModelCatalogResponse:
        data = [item for item in self._catalog if mode in item.media_types]
        return ModelCatalogResponse(data=data)
