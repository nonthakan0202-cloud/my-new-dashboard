import pandas as pd

# 1. โหลดข้อมูลดิบ
df = pd.read_csv("raw_sales_data.csv")
print(f"จำนวนข้อมูลเริ่มต้น: {len(df)} แถว")

# 2. ลบข้อมูลซ้ำ
df = df.drop_duplicates()

# 3. จัดรูปแบบวันที่ให้เป็นมาตรฐานเดียวกัน
df["Order_Date"] = df["Order_Date"].str.replace("/", "-")
df["Order_Date"] = pd.to_datetime(df["Order_Date"], format="%Y-%m-%d")

# 4. จัดการค่าว่าง (Missing Values)
median_qty = df["Quantity"].median()
df["Quantity"] = df["Quantity"].fillna(median_qty)
df["Region"] = df["Region"].fillna("Unknown")

# 5. แก้ไขค่าผิดปกติทางตรรกะ (เช่น Quantity ติดลบ)
df["Quantity"] = df["Quantity"].abs()
df.loc[df["Quantity"] > 50, "Quantity"] = median_qty

# 6. สร้างคอลัมน์คำนวณยอดขายสุทธิ (Net_Sales)
df["Net_Sales"] = df["Unit_Price"] * df["Quantity"] * (1 - df["Discount_Percent"] / 100)

# บันทึกไฟล์ที่คลีนแล้ว
df.to_csv("clean_sales_data.csv", index=False)
print("ทำความสะอาดข้อมูลสำเร็จ! บันทึกเป็น clean_sales_data.csv แล้ว")