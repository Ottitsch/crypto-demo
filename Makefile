.PHONY: install data precompute test notebook cases dashboard clean

install:
	pip install -e ".[all]"

data:
	@mkdir -p data/tagpacks data/cache data/results
	@if [ ! -d data/tagpacks/graphsense-tagpacks ]; then \
		git clone --depth 1 https://github.com/graphsense/graphsense-tagpacks \
			data/tagpacks/graphsense-tagpacks; \
	else \
		echo "graphsense-tagpacks already cloned"; \
	fi

precompute:
	python -m pof.precompute --seeds data/seeds.txt --hops 2 --out data/results/scores.parquet

precompute-no-cluster:
	python -m pof.precompute --seeds data/seeds.txt --hops 2 --no-clustering --out data/results/scores_addr.parquet

test:
	pytest

notebook:
	jupyter nbconvert --to notebook --execute notebooks/01_proof_of_funds.ipynb --output 01_proof_of_funds.ipynb

cases:
	jupyter nbconvert --to notebook --execute notebooks/02_case_studies.ipynb --output 02_case_studies.ipynb

dashboard:
	streamlit run pof/dashboard.py

clean:
	rm -rf data/results data/cache __pycache__ .pytest_cache
	find . -name "__pycache__" -type d -exec rm -rf {} +
