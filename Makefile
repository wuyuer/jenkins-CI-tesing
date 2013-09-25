# makefile for parallel kernel builds 
# (simplified from original Makefile from Olof, originally from Arnd)

ARCH            := arm
CROSS_COMPILE   := arm-linux-gnueabi-
CCACHE_DIR	:= $(PWD)/.ccache
CC              := "ccache ${CROSS_COMPILE}gcc"

export ARCH CROSS_COMPILE
export CCACHE_DIR CC

ALLCONFIGS := $(wildcard arch/${ARCH}/configs/*defconfig)
ALLTARGETS := $(patsubst arch/${ARCH}/configs/%,build-%,$(ALLCONFIGS))

CONFIG_OVERRIDES="CONFIG_DEBUG_SECTION_MISMATCH=y"

.PHONY: all buildall buildall_setup

all: buildall

build/%:
	@mkdir -p build/$*

build-%: build/%
	$(eval CFG := $(patsubst build/%,%,$<))
	@rm -f $</PASS $</FAIL
	@$(MAKE) -f Makefile O=$< $(CFG) > /dev/null
	@if $(MAKE) -f Makefile CC=$(CC) $(CONFIG_OVERRIDES) O=$< > $</build.log 2> $</build.log ; then \
		touch $</PASS; \
		RES=passed; \
	else \
		touch $</FAIL; \
		RES=failed; \
        fi ;
	@test -f $</vmlinux

clean-%: build/%
	@echo `date -R` $<
	@$(MAKE) -f Makefile O=$< clean > /dev/null
	@echo `date -R` $< done

cleanall: $(patsubst build-%,clean-%,$(ALLTARGETS))
	@

buildall_setup:
	@ccache --max-size=16G > /dev/null 2>&1
	@ccache --zero-stats > /dev/null 2>&1

buildall: buildall_setup $(ALLTARGETS)
	@ccache --show-stats
