"""Search functionality mixin for MongoFlow repositories."""

from typing import Any, Dict, List, Optional


class SearchableMixin:
    """
    Mixin to add full-text search functionality.

    Requires text index on searchable fields.

    Example:
        >>> class ArticleRepository(Repository, SearchableMixin):
        ...     collection_name = 'articles'
        ...     search_fields = ['title', 'content', 'tags']
        ...
        >>> articles = ArticleRepository()
        >>> results = articles.search('python mongodb')
    """

    search_fields: List[str] = []
    search_language: str = 'english'

    def ensure_search_index(self) -> None:
        """Create text index for search fields."""
        if self.search_fields:
            # Create compound text index
            index_spec = [(field, 'text') for field in self.search_fields]
            self.collection.create_index(
                index_spec,
                default_language=self.search_language
            )

    def search(
        self,
        query: str,
        limit: int = 20,
        min_score: Optional[float] = None,
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Perform full-text search.

        Args:
            query: Search query string
            limit: Maximum results to return
            min_score: Minimum text score threshold
            **filters: Additional filters

        Returns:
            List of matching documents with scores
        """
        # Ensure search index exists
        self.ensure_search_index()

        # Build search pipeline
        pipeline = []

        # Add text search stage
        match_stage = {
            '$match': {
                '$text': {'$search': query},
                **filters
            }
        }
        pipeline.append(match_stage)

        # Add score projection
        pipeline.append({
            '$addFields': {
                'search_score': {'$meta': 'textScore'}
            }
        })

        # Filter by minimum score if specified
        if min_score:
            pipeline.append({
                '$match': {
                    'search_score': {'$gte': min_score}
                }
            })

        # Sort by score
        pipeline.append({
            '$sort': {'search_score': -1}
        })

        # Limit results
        if limit:
            pipeline.append({'$limit': limit})

        # Execute aggregation
        results = list(self.collection.aggregate(pipeline))

        # Convert ObjectIds to strings
        from mongoflow.utils import serialize_document
        return [serialize_document(doc) for doc in results]

    def search_with_facets(
        self,
        query: str,
        facet_fields: List[str],
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search with faceted results.

        Args:
            query: Search query
            facet_fields: Fields to create facets for
            limit: Maximum results

        Returns:
            Dictionary with results and facets
        """
        # Base search pipeline
        base_match = {
            '$match': {
                '$text': {'$search': query}
            }
        }

        # Create facet stages
        facets = {
            'results': [
                {'$addFields': {'score': {'$meta': 'textScore'}}},
                {'$sort': {'score': -1}},
                {'$limit': limit}
            ]
        }

        # Add facet for each field
        for field in facet_fields:
            facets[f'{field}_facet'] = [
                {'$group': {
                    '_id': f'${field}',
                    'count': {'$sum': 1}
                }},
                {'$sort': {'count': -1}},
                {'$limit': 10}
            ]

        # Build pipeline
        pipeline = [
            base_match,
            {'$facet': facets}
        ]

        # Execute and return
        results = list(self.collection.aggregate(pipeline))
        return results[0] if results else {'results': [], **{f'{f}_facet': [] for f in facet_fields}}

    def autocomplete(
        self,
        field: str,
        prefix: str,
        limit: int = 10
    ) -> List[str]:
        """
        Autocomplete suggestions for a field.

        Args:
            field: Field to search
            prefix: Prefix to match
            limit: Maximum suggestions

        Returns:
            List of suggestions
        """
        # Use regex for prefix matching
        regex_pattern = f'^{prefix}'

        # Get distinct values matching prefix
        results = self.collection.distinct(
            field,
            {field: {'$regex': regex_pattern, '$options': 'i'}}
        )

        # Sort and limit
        results.sort()
        return results[:limit]

    def similar_to(
        self,
        document_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find documents similar to a given document.

        Args:
            document_id: Source document ID
            limit: Maximum similar documents

        Returns:
            List of similar documents
        """
        # Get the source document
        from mongoflow.utils import convert_object_id
        doc = self.collection.find_one({'_id': convert_object_id(document_id)})

        if not doc:
            return []

        # Extract searchable text from document
        search_terms = []
        for field in self.search_fields:
            if field in doc and doc[field]:
                value = doc[field]
                if isinstance(value, str):
                    search_terms.append(value)
                elif isinstance(value, list):
                    search_terms.extend([str(v) for v in value])

        if not search_terms:
            return []

        # Search for similar documents
