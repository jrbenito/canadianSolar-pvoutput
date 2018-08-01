#!/bin/bash
while true; do
	python ./canadian_reads.py
	echo "python script erro, sleeping few seconds and call it again"
	sleep 60s
done
