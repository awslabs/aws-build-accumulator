LITANI = ../../../litani add-job
OUT_DIR = output

default: $(OUT_DIR)/all.txt

$(OUT_DIR)/1.txt:
	$(LITANI)               \
	  --outputs $@          \
	  --ci-stage build      \
	  --pipeline 1          \
	  --command "touch $@"  \
	  #

$(OUT_DIR)/2.txt:
	$(LITANI)               \
	  --outputs $@          \
	  --ci-stage build      \
	  --pipeline 2          \
	  --command "touch $@"  \
	  #

$(OUT_DIR)/3.txt:
	$(LITANI)               \
	  --outputs $@          \
	  --ci-stage build      \
	  --pipeline 3          \
	  --command "touch $@"  \
	  #

$(OUT_DIR)/all.txt: $(OUT_DIR)/1.txt $(OUT_DIR)/2.txt $(OUT_DIR)/3.txt
	$(LITANI)             \
	  --inputs $^         \
	  --outputs $@        \
	  --stdout-file $@    \
	  --ci-stage test     \
	  --pipeline all      \
	  --command "cat $^"  \
	  #
