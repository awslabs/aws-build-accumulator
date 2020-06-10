index.html: head.html index.tmp.html foot.html
	cat $^ > $@

.INTERMEDIATE: index.tmp.html
index.tmp.html: index.md
	markdown $^ > $@
