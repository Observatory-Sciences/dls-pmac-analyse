# This line tells make that anything defined before this point is not to be
# used as an msi include dir
CONFIGURE :=
NON_MSI_VARS := $(.VARIABLES)

# include module definitions
ifneq ($(wildcard configure/RELEASE),)
    # if controller specific ./configure/RELEASE exists use it
    CONFIGURE := configure
    include configure/RELEASE
else
    # otherwise use the global one
    CONFIGURE := ../configure
    include ../configure/RELEASE
endif

# include rules
include $(PMACUTIL)/configure/PMC_RULES
