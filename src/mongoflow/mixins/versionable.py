"""Version control mixin for MongoFlow repositories."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from bson import ObjectId


class VersionableMixin:
    """
    Mixin to add version control to documents.

    Tracks document versions and maintains history.

    Example:
        >>> class DocumentRepository(Repository, VersionableMixin):
        ...     collection_name = 'documents'
        ...     max_versions = 10
        ...
        >>> docs = DocumentRepository()
        >>> doc = docs.create({'content': 'v1'})
        >>> docs.update_with_version(doc['_id'], {'content': 'v2'})
        >>> history = docs.get_version_history(doc['_id'])
    """

    max_versions: int = 10  # Maximum versions to keep
    version_field: str = '_version'
    history_field: str = '_history'

    def _prepare_for_insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add initial version when creating document."""
        data = super()._prepare_for_insert(data) if hasattr(super(), '_prepare_for_insert') else data

        # Set initial version
        data[self.version_field] = 1
        data[self.history_field] = []

        return data

    def update_with_version(self, id: Union[str, ObjectId], data: Dict[str, Any]) -> bool:
        """
        Update document and create a new version.

        Args:
            id: Document ID
            data: Update data

        Returns:
            True if successful
        """
        from mongoflow.utils import convert_object_id

        id = convert_object_id(id)

        # Get current document
        current = self.collection.find_one({'_id': id})
        if not current:
            return False

        # Create version entry
        version_entry = {
            'version': current.get(self.version_field, 1),
            'data': {k: v for k, v in current.items()
                    if k not in ['_id', self.version_field, self.history_field]},
            'created_at': current.get('updated_at', datetime.utcnow())
        }

        # Prepare update
        update_data = self._prepare_for_update(data) if hasattr(self, '_prepare_for_update') else data

        # Increment version
        new_version = current.get(self.version_field, 1) + 1

        # Update document with new version
        result = self.collection.update_one(
            {'_id': id},
            {
                '$set': {
                    **update_data,
                    self.version_field: new_version
                },
                '$push': {
                    self.history_field: {
                        '$each': [version_entry],
                        '$slice': -self.max_versions  # Keep only last N versions
                    }
                }
            }
        )

        return result.modified_count > 0

    def get_version(self, id: Union[str, ObjectId], version: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific version of a document.

        Args:
            id: Document ID
            version: Version number

        Returns:
            Document at specified version or None
        """
        from mongoflow.utils import convert_object_id, serialize_document

        id = convert_object_id(id)

        # Get document with history
        doc = self.collection.find_one({'_id': id})
        if not doc:
            return None

        # Current version
        current_version = doc.get(self.version_field, 1)

        if version == current_version:
            # Return current version
            return serialize_document(doc)

        # Look in history
        history = doc.get(self.history_field, [])
        for entry in history:
            if entry.get('version') == version:
                # Reconstruct document at this version
                versioned_doc = {
                    '_id': str(id),
                    **entry['data'],
                    self.version_field: version
                }
                return versioned_doc

        return None

    def get_version_history(self, id: Union[str, ObjectId]) -> List[Dict[str, Any]]:
        """
        Get version history for a document.

        Args:
            id: Document ID

        Returns:
            List of version entries
        """
        from mongoflow.utils import convert_object_id

        id = convert_object_id(id)

        doc = self.collection.find_one(
            {'_id': id},
            {self.history_field: 1, self.version_field: 1}
        )

        if not doc:
            return []

        history = doc.get(self.history_field, [])

        # Add current version to history
        current_version = {
            'version': doc.get(self.version_field, 1),
            'is_current': True,
            'created_at': datetime.utcnow().isoformat()
        }

        return history + [current_version]

    def revert_to_version(self, id: Union[str, ObjectId], version: int) -> bool:
        """
        Revert document to a specific version.

        Args:
            id: Document ID
            version: Version to revert to

        Returns:
            True if successful
        """
        # Get the specified version
        versioned_doc = self.get_version(id, version)
        if not versioned_doc:
            return False

        # Remove metadata fields
        versioned_doc.pop('_id', None)
        versioned_doc.pop(self.version_field, None)

        # Update document with versioned data
        return self.update_with_version(id, versioned_doc)

    def compare_versions(
        self,
        id: Union[str, ObjectId],
        version1: int,
        version2: int
    ) -> Dict[str, Any]:
        """
        Compare two versions of a document.

        Args:
            id: Document ID
            version1: First version
            version2: Second version

        Returns:
            Dictionary with differences
        """
        v1 = self.get_version(id, version1)
        v2 = self.get_version(id, version2)

        if not v1 or not v2:
            return {'error': 'One or both versions not found'}

        # Find differences
        added = {}
        removed = {}
        changed = {}

        all_keys = set(v1.keys()) | set(v2.keys())

        for key in all_keys:
            if key in [self.version_field, self.history_field, '_id']:
                continue

            if key in v1 and key not in v2:
                removed[key] = v1[key]
            elif key not in v1 and key in v2:
                added[key] = v2[key]
            elif v1.get(key) != v2.get(key):
                changed[key] = {'from': v1[key], 'to': v2[key]}

        return {
            'version1': version1,
            'version2': version2,
            'added': added,
            'removed': removed,
            'changed': changed
        }

    def prune_versions(self, id: Union[str, ObjectId], keep: int = 5) -> bool:
        """
        Prune old versions keeping only the most recent ones.

        Args:
            id: Document ID
            keep: Number of versions to keep

        Returns:
            True if successful
        """
        from mongoflow.utils import convert_object_id

        id = convert_object_id(id)

        # Update to keep only last N versions
        result = self.collection.update_one(
            {'_id': id},
            {
                '$push': {
                    self.history_field: {
                        '$each': [],
                        '$slice': -keep
                    }
                }
            }
        )

        return result.modified_count > 0
