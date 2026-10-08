# Konteks MRP Material Emas ANTAM

Konteks ini menyamakan istilah perencanaan kebutuhan material untuk target produksi emas dan menjadi acuan saat membaca tiga tabel MRP.

## Bahasa

**Target produksi emas**:
Jumlah emas batangan yang hendak diproduksi dalam satu perhitungan, dinyatakan dalam kg emas.
_Hindari_: Target bahan, target reagen

**Formula material**:
Rasio standar kebutuhan satu material untuk menghasilkan 1 kg emas pada tahap proses tertentu.
_Hindari_: Harga material, komposisi stok

**Kebutuhan bruto**:
Total kebutuhan material sebelum dikurangi ketersediaan, dihitung dari target produksi dan formula material.
_Hindari_: Kebutuhan neto, kebutuhan pembelian

**Stok gudang**:
Material yang sudah tersedia secara fisik di gudang dan dapat dipakai untuk memenuhi kebutuhan produksi.
_Hindari_: Stok tersedia total, stok berjalan

**Stok di jalan**:
Material yang sudah dipesan atau dikirim tetapi belum diterima di gudang.
_Hindari_: Stok transit, stok gudang

**Ketersediaan**:
Gabungan stok gudang dan stok di jalan yang diperhitungkan untuk menutup kebutuhan bruto.
_Hindari_: Kebutuhan tersedia, stok bersih

**Kebutuhan neto**:
Jumlah material yang masih harus dipenuhi setelah ketersediaan dikurangkan dari kebutuhan bruto; nilainya tidak boleh kurang dari nol.
_Hindari_: Sisa bruto, total kebutuhan

**Summary kebutuhan pengadaan**:
Ringkasan material per bahan yang menyajikan kebutuhan neto dan estimasi nilai pengadaannya.
_Hindari_: Summary stok, daftar formula

**Material tertutup stok**:
Material yang seluruh kebutuhan brutonya sudah dipenuhi oleh ketersediaan gudang dan/atau stok di jalan.
_Hindari_: Material selesai, material nol
