const voiceBtn = document.getElementById("voiceBtn");
const searchInput = document.getElementById("searchText");
const form = document.getElementById("searchForm");
const statusText = document.getElementById("voiceStatus");

const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {

    const recognition = new SpeechRecognition();

    recognition.lang = "ru-RU";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    voiceBtn.onclick = () => {

        statusText.innerText = "🎤 Listening...";
        voiceBtn.classList.add("animate-pulse");

        recognition.start();
    };

    recognition.onresult = function(event){

        const text = event.results[0][0].transcript;

        searchInput.value = text;

        statusText.innerText = "AI tushundi: " + text;

        setTimeout(()=>{
            form.submit();
        },800)

    };

    recognition.onerror = function(){
        statusText.innerText = "Xatolik yuz berdi";
    };

    recognition.onend = function(){
        voiceBtn.classList.remove("animate-pulse");
    };

}
else{
    statusText.innerText = "Voice search bu brauzerda ishlamaydi";
}