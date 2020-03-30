#!/bin/bash
while true; do
	python3 ./canadian_reads.py
	echo "python3 script erro, sleeping few seconds and call it again"
	sleep 60s
done
