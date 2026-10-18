import qrcode

url = "https://verify.chasescroll.com/profile/share/6ad322ac203c925c74c86a00"

qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4,
)
qr.add_data(url)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save("chasescroll_profile_qr.png")
