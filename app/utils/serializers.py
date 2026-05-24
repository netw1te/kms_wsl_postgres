from app.models.info_object import InfoObject


def serialize_info_object(obj: InfoObject) -> dict:
    """Сериализует InfoObject в словарь для Pydantic модели"""
    return {
        "id": obj.id,
        "title": obj.title,
        "content": obj.content,
        "source": obj.source,
        "author": obj.author,
        "url": obj.url,
        "doi": obj.doi,
        "publication_title": obj.publication_title,
        "publication_date_from_raw": obj.publication_date_from_raw,
        "publication_date_to_raw": obj.publication_date_to_raw,
        "publication_date_from": obj.publication_date_from,
        "publication_date_to": obj.publication_date_to,
        "publication_date_raw": obj.publication_date_raw,
        "publication_date": obj.publication_date,
        "tags": [tag.name for tag in obj.tags],
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
        "created_by": obj.created_by,
        "deletion_flag": bool(obj.deletion_flag),
        "deletion_reason": obj.deletion_reason,
        "deleted_by": obj.deleted_by,
        "deleted_at": getattr(obj, "deleted_at", None),
        "replacement_info_object_id": obj.replacement_info_object_id,
    }