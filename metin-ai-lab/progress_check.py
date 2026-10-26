scores = [50, 75, 90, 85, 85]
scores.append(100)
progress = scores[-1] - scores[-2]
print("Son iki sinav arasindaki fark:", progress)
if progress > 0:
    print("Puanin artti!")
elif progress < 0:
    print("Puanin dustu.")
else:
    print("Puanin degismedi.")
