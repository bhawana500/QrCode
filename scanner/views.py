from django.shortcuts import render
from.models import QRCode
import qrcode
from django.core.files.storage import FileSystemStorage
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
from pathlib import Path
import cv2
from PIL import Image
# Create your views here.
def generate_qr(request):
    qr_image_url = None
    if request.method == "POST":
        mobile_number = request.POST.get('mobile_number')
        data = request.POST.get('qr_data')
        
        # Validate The mobile number
        if not mobile_number or len(mobile_number)!=10 or not mobile_number.isdigit():
            return render(request,'scanner/generate.html',{'error':'Invalid Mobile Number'})
        
        #Generate the QRCode image with mobile number and Data
        qr_content = f"{data}|{mobile_number}"
        qr = qrcode.make(qr_content)
        
        # creating BytesIO stream
        qr_image_io = BytesIO()
        
        #saving qrcode image to  qr_image_io 
        qr.save(qr_image_io,format='PNG')
        
        #reset the position of the stream
        qr_image_io.seek(0)
        
        #define the storage locationfor the qrcode images
        qr_storage_path = settings.MEDIA_ROOT/'qr_codes'
        fs = FileSystemStorage(location=qr_storage_path, base_url='/media/qr_codes/')
        filename = f"{data}_{mobile_number}.png"
        
        # to read 
        qr_image_content = ContentFile(qr_image_io.read(),name=filename)
        
        #saving it
        filepath = fs.save(filename,qr_image_content)
        qr_image_url = fs.url(filename)
        
        #save it into database
        qr_obj=QRCode.objects.create(data=data,mobile_number=mobile_number)
        qr_obj.save()
    return render(request,'scanner/generate.html',{'qr_image_url':qr_image_url})




def scan_qr(request):
    result = None
    if request.method == "POST" and request.FILES.get('qr_image'):
        mobile_number = request.POST.get('mobile_number')
        data = request.POST.get('data')
        qr_image = request.FILES['qr_image']
        # Validate The mobile number
        if not mobile_number or len(mobile_number)!=10 or not mobile_number.isdigit():
            return render(request,'scanner/scan.html',{'error':'Invalid Mobile Number'})

        #save the Uploaded Image
        fs = FileSystemStorage()
        filename = fs.save(qr_image.name,qr_image)
        image_path = Path(fs.location) / filename
        
        try:
            #ope the image and decode it
            image = cv2.imread(str(image_path))
            detector = cv2.QRCodeDetector()
            qr_content, bbox, _ = detector.detectAndDecode(image)
            if qr_content:
                #Get the data from the first decoded image         
                qr_data, qr_mobile_number = qr_content.split('|')
                
                # Check if the data exists in the QRCode model with the provided mobile number
                qr_entry = QRCode.objects.filter(
                    data=qr_data,
                    mobile_number=qr_mobile_number).first()
                if qr_entry and qr_mobile_number == mobile_number:
                    result = "Scan Success: Valid QRCode for the provided mobile number"
                
                    # Delete the specific QR code entry from database
                    # qr_entry.delete()
                
                    # delete the Qrcode from the 'media/qr_codes' Directory
                    qr_image_path = settings.MEDIA_ROOT / 'qr_codes' / f"{qr_data}_{qr_mobile_number}.png"
                    
                    if qr_image_path.exists():
                        qr_image_path.unlink() # Deletes the qrcode image
                    
                    if image_path.exists():
                        image_path.unlink() # Deletes the qrcode image
            
                else:
                    result = "Scan FAILED: Invalid QRCode or the mobile number mismatched"  
                      
            else: 
                result = "No QR Code detected in the image"
                
        except Exception as e:
            result = f"error processing the image: {str(e)}"
            
        finally: 
            # Ensure the Uploaded image is deleted regardless of the RESULT
            if image_path.exists():
                image_path.unlink()
        
    return render(request,'scanner/scan.html',{'result':result})

