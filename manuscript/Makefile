LATEXMK ?= latexmk

# pdfTeX honors SOURCE_DATE_EPOCH for reproducible PDF timestamps/IDs.  A fixed
# epoch makes the committed manuscript a deterministic build artifact rather
# than a machine-local export.
export SOURCE_DATE_EPOCH ?= 0
export FORCE_SOURCE_DATE ?= 1

.PHONY: all clean rebuild

all: r005_sycamore_routing.pdf

r005_sycamore_routing.pdf: r005_sycamore_routing.tex
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error r005_sycamore_routing.tex

rebuild: clean all

clean:
	$(LATEXMK) -C r005_sycamore_routing.tex
