from bs4 import BeautifulSoup

with open("html.html", encoding="utf-8") as file:
    html = file.read()

soup = BeautifulSoup(html, "html.parser")
print(soup.title.string)

rows = soup.find_all("tr")
print(f"Found {len(rows)} rows")
for i in range(1, 6):
    print(i, rows[i].get_text(" | ", strip=True))

print()
print(rows[2])
print()
print(rows[3])
