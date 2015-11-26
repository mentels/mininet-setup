Models=(proc_per_switch regular)
Cores=(1 2)
# Hosts=(10 20 50 100)
Hosts=(10 20 50)
Hosts2=(100 200)

for m in ${Models[*]}; do 
    for c in ${Cores[*]}; do
        for h in ${Hosts[*]}; do
            sudo -E ./cluster.py \
            --mn-hosts localhost mn2 mn3 \
            --hosts $h \
            --switches 4 \
            --iterations 1000 \
            --mode $m \
            --schedulers-online $c 
        done;
    done
done


for m in ${Models[*]}; do 
    for c in ${Cores[*]}; do
        for h in ${Hosts2[*]}; do
            sudo -E ./cluster.py \
            --mn-hosts localhost mn2 mn3 \
            --hosts $h \
            --switches 4 \
            --iterations 1000 \
            --mode $m \
            --schedulers-online $c 
        done;
    done
done

