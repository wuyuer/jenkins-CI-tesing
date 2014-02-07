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

.PHONY: all buildall ccache_setup kjh

all: buildall

build/%:
	@mkdir -p build/$*

#build-%: build/%
%_defconfig: build/%_defconfig
	$(eval CFG := $(patsubst build/%,%,$<))
	@rm -f $</PASS $</FAIL $</vmlinux
	@$(MAKE) -f Makefile O=$< $(CFG) > /dev/null
	@if $(MAKE) -f Makefile CC=$(CC) $(CONFIG_OVERRIDES) O=$< > $</build.log 2> $</build.log ; then \
		touch $</PASS; \
		RES=passed; \
	else \
		touch $</FAIL; \
		RES=failed; \
        fi ; \
	WARN=`grep -i warning: $</build.log | fgrep -v "TODO: return_address should use unwind tables" | wc -l` ; \
	SECT=`grep "Section mismatch" $</build.log | wc -l` ; \
	printf "   %-25s  %s, %3s warnings, %2s section mismatches\n" $(CFG) $$RES $$WARN $$SECT 
	@test -f $</vmlinux

clean-%: build/%
	@echo `date -R` $<
	@$(MAKE) -f Makefile O=$< clean > /dev/null
	@echo `date -R` $< done

cleanall: $(patsubst build-%,clean-%,$(ALLTARGETS))
	@

ccache_setup:
	@ccache --max-size=16G > /dev/null 2>&1
	@ccache --zero-stats > /dev/null 2>&1

buildall: ccache_setup $(ALLTARGETS)
	@ccache --show-stats
