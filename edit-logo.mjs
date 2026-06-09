import ZAI from 'z-ai-web-dev-sdk';
import fs from 'fs';

async function main() {
  try {
    const zai = await ZAI.create();
    
    const imageBuffer = fs.readFileSync('/home/z/my-project/upload/agdi-logo.png');
    const base64Image = imageBuffer.toString('base64');
    const dataUrl = `data:image/png;base64,${base64Image}`;
    
    const response = await zai.images.generations.edit({
      prompt: "Add the word 'automation' in lowercase text directly below the existing 'agdi' logo text, seamlessly integrated as if it was always part of the original design. The text should use the exact same rounded sans-serif bold font style. Split colors: 'automa' in the same green as 'ag', and 'tion' in the same blue as 'di'. The new text should be slightly smaller than the main text, with matching tight letter spacing. Keep original logo untouched. Transparent background. Clean, flat design.",
      images: [{ url: dataUrl }],
      size: '1024x1024'
    });
    
    const imageBase64 = response.data[0].base64;
    const buffer = Buffer.from(imageBase64, 'base64');
    fs.writeFileSync('/home/z/my-project/download/agdi-logo-automation-v1.png', buffer);
    console.log('SUCCESS: Image saved to /home/z/my-project/download/agdi-logo-automation-v1.png');
    console.log('File size:', buffer.length, 'bytes');
  } catch (error) {
    console.error('Error:', error.message);
  }
}

main();
