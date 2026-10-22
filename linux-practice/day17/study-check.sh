#!/bin/bash

read -r -p "Bugun kac dakika calisacaksin? " minutes
if ! [[ "$minutes" =~ ^[0-9]+$ ]]; then
    echo "Lutfen sadece sayi gir!"
    exit 1
fi

if [ "$minutes" -ge 60 ]; then
    echo "Mukemmel!"
elif [ "$minutes" -ge 30 ]; then
    echo "Hedef tamam!"
else
    echo "Biraz daha calis!"
fi
