LATEXMK ?= latexmk

.PHONY: all clean

all: r005_sycamore_routing.pdf

r005_sycamore_routing.pdf: r005_sycamore_routing.tex
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error r005_sycamore_routing.tex

clean:
	$(LATEXMK) -C r005_sycamore_routing.tex
