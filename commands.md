# Storage & Cost Analysis: Metadata Improvements

## Current Baseline (Your Existing Schema)

### Current Metadata (8 fields)

# for user Imtiazhashmi@gmail.com
<!--

.\memoenv\Scripts\python evaluation\benchmark.py --user-id 465aaa1c-beb9-48d7-932a-31d11760e764 --num-queries 15 --metrics mrr,p@5,llm,latency --save-path evaluation/results/run_1.json


memoenv\Scripts\python.exe scripts\reset_db.py "465aaa1c-beb9-48d7-932a-31d11760e764"


memoenv\Scripts\python.exe scripts\ingest.py --full --user-id "465aaa1c-beb9-48d7-932a-3
1d11760e764"

python scripts/embed.py --full --user-id 465aaa1c-beb9-48d7-932a-31d11760e764


python .\evaluation
\synthetic_data.py --user-id 465aaa1c-beb9-48d7-932a-31d11760e764

 .\memoenv\Scripts\python evaluation\benchmark.py --user-id 465aaa1c-beb9-48d7-932a-31d11760e764 --num-queries 15

.\memoenv\Scripts\python evaluation\benchmark.py --user-id 465aaa1c-beb9-48d7-932a-31d11760e764 --num-queries 15 --metrics mrr,p@5,latency


.\memoenv\Scripts\python evaluation\benchmark.py --user-id 465aaa1c-beb9-48d7-932a-31d11760e764 --num-queries 15 --save-path evaluation/results/run_1.json -->

# early results
MRR            : 0.386
PRECISION@5    : 0.500
LATENCY_MS     : 5428.071
LLM_RELEVANCE  : 3.533

# after BM25 and RRF

MRR            : 0.267
PRECISION@5    : 0.400
LATENCY_MS     : 8375.739
LLM_RELEVANCE  : 2.867

#chroma db limits that was 10 initially , increased the #depth 10k docs, retrieval depth to 60k


MRR            : 0.350
PRECISION@5    : 0.400
LATENCY_MS     : 13263.055
LLM_RELEVANCE  : 3.533


after errors and re indexing

MRR            : 0.364
PRECISION@5    : 0.400
LATENCY_MS     : 5569.330
LLM_RELEVANCE  : 3.167
