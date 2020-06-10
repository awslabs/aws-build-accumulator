$data << EOD
{% for job in jobs -%}
0.4 {{ job["duration"] }} {{ job["pipeline"] }}
{% endfor %}{# job in jobs #}
EOD

set output "{{ url }}"
set terminal svg noenhanced size 400,400

set border 2 linecolor "#263238"
set ytics nomirror tc "#263238" font "Helvetica,12"
unset xtics
unset key

set ylabel "seconds" tc "#263238" font "Helvetica,12"

set title "Runtime for {{ group_name }}" tc "#263238" font "Helvetica,12"

set xrange [0:1]

set boxwidth 0.2

plot '$data' using (0.2):2 with boxplot lc "#263238", \
      '' using 1:2:3 with labels left tc "#263238" font "Helvetica,10"
