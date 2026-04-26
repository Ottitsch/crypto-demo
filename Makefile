.PHONY: install data precompute test notebook clean

install:
	pip install -e ".[dev,notebook]"

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

test:
	pytest

notebook:
	jupyter nbconvert --to notebook --execute notebooks/01_proof_of_funds.ipynb --output 01_proof_of_funds.ipynb

clean:
	rm -rf data/results data/cache __pycache__ .pytest_cache
	find . -name "__pycache__" -type d -exec rm -rf {} +
