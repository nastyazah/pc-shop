ARG OPENSEARCH_VERSION=3.6.0
FROM opensearchproject/opensearch:${OPENSEARCH_VERSION}
# морфологія української (Lucene UkrainianMorfologikAnalyzer)
RUN /usr/share/opensearch/bin/opensearch-plugin install --batch analysis-ukrainian
