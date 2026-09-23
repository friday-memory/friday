"""Friday LangChain Integration — Custom BaseRetriever."""

from typing import Any, List, Optional

from ..client import Friday

try:
    from langchain_core.callbacks import CallbackManagerForRetrieverRun
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever

    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False
    BaseRetriever = None  # type: ignore
    Document = None  # type: ignore
    CallbackManagerForRetrieverRun = None  # type: ignore


if _HAS_LANGCHAIN:

    class FridayRetriever(BaseRetriever):  # type: ignore[misc]
        """LangChain Retriever for Friday Cognitive Memory Layer.

        Example:
            ```python
            from friday.integrations.langchain import FridayRetriever

            retriever = FridayRetriever(api_key="secret", base_url="http://localhost:8000")
            docs = retriever.invoke("What database do we use?")
            ```
        """

        api_key: Optional[str] = None
        base_url: Optional[str] = "http://localhost:8000"
        project: str = "default"

        def _get_relevant_documents(
            self, query: str, *, run_manager: Optional[CallbackManagerForRetrieverRun] = None
        ) -> List[Document]:
            with Friday(api_key=self.api_key, base_url=self.base_url) as client:
                res = client.search(query=query, project=self.project)
                docs = []
                results = res.get("results", {})

                # Parse facts
                for fact in results.get("layer2_facts", []):
                    docs.append(Document(page_content=fact, metadata={"source": "friday_facts"}))

                # Parse semantic chunks
                for mem in results.get("layer3_semantic", []):
                    docs.append(Document(page_content=mem, metadata={"source": "friday_semantic"}))

                return docs

else:

    class FridayRetriever:  # type: ignore[no-redef]
        """Stub FridayRetriever when langchain-core is not installed."""

        def __init__(
            self,
            api_key: Optional[str] = None,
            base_url: Optional[str] = "http://localhost:8000",
            project: str = "default",
            **kwargs: Any,
        ):
            self.api_key = api_key
            self.base_url = base_url
            self.project = project

        def _get_relevant_documents(self, query: str, *args: Any, **kwargs: Any) -> Any:
            raise ImportError(
                "langchain-core is required to use FridayRetriever. "
                "Install it via: pip install 'friday-memory[langchain]' or pip install langchain-core"
            )

        def invoke(self, input: str, *args: Any, **kwargs: Any) -> Any:
            return self._get_relevant_documents(input, *args, **kwargs)
