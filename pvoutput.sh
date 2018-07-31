#!/bin/bash
while true; do
	HORA=$(date +"%H")
	if [[ $HORA -gt 04 && $HORA -lt 21 ]]; then
		#until python ./read_values.py; do
		until python ./canadian_reads.py; do
			echo error
			sleep 5s
		done
	fi
	sleep 5m
done
