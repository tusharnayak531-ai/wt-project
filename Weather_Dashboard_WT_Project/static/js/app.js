let chart;
let debounceTimer;
let activeData = null;

const $ = id => document.getElementById(id);
const fmt = (v, digits=0) => Number(v ?? 0).toFixed(digits);
const moneyless = v => v == null ? "--" : Math.round(v);
const esc = s => String(s ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));


function weatherMeta(code){
  code=Number(code||0);
  const m={
    0:["Clear sky","clear"],1:["Mainly clear","clear"],2:["Partly cloudy","cloudy"],3:["Overcast","cloudy"],
    45:["Fog","fog"],48:["Rime fog","fog"],51:["Light drizzle","rain"],53:["Drizzle","rain"],55:["Heavy drizzle","rain"],
    56:["Freezing drizzle","rain"],57:["Heavy freezing drizzle","rain"],61:["Light rain","rain"],63:["Rain","rain"],
    65:["Heavy rain","rain"],66:["Freezing rain","rain"],67:["Heavy freezing rain","rain"],71:["Light snow","snow"],
    73:["Snow","snow"],75:["Heavy snow","snow"],77:["Snow grains","snow"],80:["Light showers","rain"],81:["Showers","rain"],
    82:["Heavy showers","storm"],85:["Snow showers","snow"],86:["Heavy snow showers","snow"],95:["Thunderstorm","storm"],
    96:["Thunderstorm with hail","storm"],99:["Severe thunderstorm","storm"]
  };
  return m[code]||["Weather","cloudy"];
}

async function geocodeOne(city){
  const u=new URL("https://geocoding-api.open-meteo.com/v1/search");
  u.search=new URLSearchParams({name:city,count:"1",language:"en",format:"json"}).toString();
  const r=await fetch(u);
  if(!r.ok) throw new Error("Location search failed.");
  const d=await r.json();
  const x=d.results && d.results[0];
  if(!x) throw new Error("City not found. Try another spelling.");
  return {name:x.name,admin1:x.admin1||null,country:x.country||null,latitude:x.latitude,longitude:x.longitude,timezone:x.timezone||null};
}

async function fetchWeatherDirect(params){
  let location,lat,lon;
  if(params.city){
    location=await geocodeOne(params.city);
    lat=location.latitude; lon=location.longitude;
  }else{
    lat=Number(params.lat); lon=Number(params.lon);
    location={name:"Current location",admin1:null,country:null,latitude:lat,longitude:lon,timezone:null};
  }

  const f=new URL("https://api.open-meteo.com/v1/forecast");
  f.search=new URLSearchParams({
    latitude:String(lat),longitude:String(lon),
    current:"temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
    hourly:"temperature_2m,apparent_temperature,precipitation_probability,weather_code,wind_speed_10m,relative_humidity_2m",
    daily:"weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,sunrise,sunset,uv_index_max,precipitation_probability_max,wind_speed_10m_max",
    temperature_unit:"celsius",wind_speed_unit:"kmh",precipitation_unit:"mm",timezone:"auto",forecast_days:"7"
  }).toString();

  const a=new URL("https://air-quality-api.open-meteo.com/v1/air-quality");
  a.search=new URLSearchParams({
    latitude:String(lat),longitude:String(lon),
    current:"us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone",
    timezone:"auto"
  }).toString();

  const wr=await fetch(f);
  if(!wr.ok) throw new Error("Weather service is temporarily unavailable. Please try again.");
  const wx=await wr.json();

  let aq={};
  try{
    const ar=await fetch(a);
    if(ar.ok) aq=await ar.json();
  }catch(e){}

  const meta=weatherMeta(wx.current && wx.current.weather_code);
  const codes=(wx.daily && wx.daily.weather_code)||[];
  return {
    location:location,
    timezone:wx.timezone,
    timezone_abbreviation:wx.timezone_abbreviation,
    elevation:wx.elevation,
    current:wx.current||{},
    condition:meta[0],
    theme:meta[1],
    hourly:wx.hourly||{},
    daily:wx.daily||{},
    daily_labels:codes.map(function(x){return weatherMeta(x)[0]}),
    air_quality:(aq.current||{})
  };
}

function iconFor(code, isDay=1){
  code = Number(code);
  if(code===0) return isDay ? "☀️" : "🌙";
  if([1,2].includes(code)) return isDay ? "🌤️" : "☁️";
  if(code===3) return "☁️";
  if([45,48].includes(code)) return "🌫️";
  if([51,53,55,56,57,61,63,65,66,67,80,81].includes(code)) return "🌧️";
  if(code===82) return "⛈️";
  if([71,73,75,77,85,86].includes(code)) return "🌨️";
  if([95,96,99].includes(code)) return "⛈️";
  return "☁️";
}

function windCompass(deg){
  const d=["N","NE","E","SE","S","SW","W","NW"];
  return d[Math.round((Number(deg)||0)/45)%8];
}

function aqiLabel(aqi){
  aqi=Number(aqi);
  if(!aqi) return "Unavailable";
  if(aqi<=50) return "Good";
  if(aqi<=100) return "Moderate";
  if(aqi<=150) return "Unhealthy for sensitive groups";
  if(aqi<=200) return "Unhealthy";
  if(aqi<=300) return "Very unhealthy";
  return "Hazardous";
}

function uvLabel(uv){
  uv=Number(uv);
  if(uv<3) return "Low";
  if(uv<6) return "Moderate";
  if(uv<8) return "High";
  if(uv<11) return "Very high";
  return "Extreme";
}

function humanTime(iso){
  if(!iso) return "--";
  const part=String(iso).split("T")[1] || "";
  const [h,m]=part.split(":");
  let hh=Number(h), suffix=hh>=12?"PM":"AM";
  hh=hh%12 || 12;
  return `${hh}:${m} ${suffix}`;
}

function dayLabel(iso, index){
  const d=new Date(iso+"T12:00:00");
  if(index===0) return "Today";
  return d.toLocaleDateString("en-US",{weekday:"short"});
}

function showError(msg){
  const box=$("errorBox");
  box.textContent=msg;
  box.classList.add("show");
  setTimeout(()=>box.classList.remove("show"),5000);
}

function setLoading(v){ $("loader").classList.toggle("show", v); }

function currentHourStart(hourlyTimes, currentIso){
  if(!hourlyTimes?.length) return 0;
  const hour = String(currentIso || "").slice(0,13);
  const idx = hourlyTimes.findIndex(t => String(t).slice(0,13) === hour);
  return idx >= 0 ? idx : 0;
}

function render(data){
  activeData=data;
  document.body.dataset.theme=data.theme || "clear";

  const loc=data.location || {}, c=data.current || {}, d=data.daily || {}, h=data.hourly || {}, aq=data.air_quality || {};
  const cityParts=[loc.admin1,loc.country].filter(Boolean);

  $("cityName").textContent=loc.name || "Current location";
  $("cityMeta").textContent=cityParts.join(", ") || `${fmt(loc.latitude,2)}, ${fmt(loc.longitude,2)}`;
  $("forecastLocation").textContent=loc.name || "Current location";
  $("localTime").textContent=humanTime(c.time);
  $("currentTemp").textContent=`${moneyless(c.temperature_2m)}°`;
  $("condition").textContent=data.condition || "Weather";
  $("feelsLike").textContent=`Feels like ${moneyless(c.apparent_temperature)}°`;
  $("weatherIcon").textContent=iconFor(c.weather_code,c.is_day);

  $("todayHigh").textContent=`${moneyless(d.temperature_2m_max?.[0])}°`;
  $("todayLow").textContent=`${moneyless(d.temperature_2m_min?.[0])}°`;
  $("todayRain").textContent=`${moneyless(d.precipitation_probability_max?.[0])}%`;

  $("humidity").textContent=`${moneyless(c.relative_humidity_2m)}%`;
  $("wind").textContent=`${moneyless(c.wind_speed_10m)} km/h`;
  $("windDir").textContent=`${windCompass(c.wind_direction_10m)} • gusts ${moneyless(c.wind_gusts_10m)} km/h`;
  $("pressure").textContent=`${moneyless(c.pressure_msl)} hPa`;
  $("clouds").textContent=`${moneyless(c.cloud_cover)}%`;
  $("uv").textContent=fmt(d.uv_index_max?.[0],1);
  $("uvText").textContent=`${uvLabel(d.uv_index_max?.[0])} • daily maximum`;
  $("aqi").textContent=aq.us_aqi ?? "--";
  $("aqiText").textContent=aqiLabel(aq.us_aqi);

  $("sunrise").textContent=humanTime(d.sunrise?.[0]);
  $("sunset").textContent=humanTime(d.sunset?.[0]);
  $("pm25").textContent=aq.pm2_5 == null ? "--" : `${fmt(aq.pm2_5,1)} μg/m³`;
  $("pm10").textContent=aq.pm10 == null ? "--" : `${fmt(aq.pm10,1)} μg/m³`;
  $("ozone").textContent=aq.ozone == null ? "--" : `${fmt(aq.ozone,1)} μg/m³`;
  $("no2").textContent=aq.nitrogen_dioxide == null ? "--" : `${fmt(aq.nitrogen_dioxide,1)} μg/m³`;

  renderHourly(h,c.time);
  renderDaily(d,data.daily_labels || []);
}

function renderHourly(h,currentTime){
  const start=currentHourStart(h.time,currentTime);
  const end=Math.min(start+24,(h.time||[]).length);
  let html="";
  for(let i=start;i<end;i++){
    const t=h.time[i];
    html+=`<div class="hour-card ${i===start?"now":""}">
      <small>${i===start?"Now":humanTime(t).replace(":00","")}</small>
      <div class="wi">${iconFor(h.weather_code?.[i],1)}</div>
      <b>${moneyless(h.temperature_2m?.[i])}°</b>
      <p>☂ ${moneyless(h.precipitation_probability?.[i])}%</p>
    </div>`;
  }
  $("hourlyStrip").innerHTML=html;

  const labels=(h.time||[]).slice(start,end).map(t=>humanTime(t).replace(":00",""));
  const temps=(h.temperature_2m||[]).slice(start,end);
  const rain=(h.precipitation_probability||[]).slice(start,end);

  if(chart) chart.destroy();
  const ctx=$("hourlyChart").getContext("2d");
  chart=new Chart(ctx,{
    type:"line",
    data:{labels,datasets:[
      {label:"Temperature °C",data:temps,yAxisID:"y",tension:.38,borderWidth:2,pointRadius:1.5,fill:true,backgroundColor:"rgba(255,138,91,.10)",borderColor:"#ff8a5b"},
      {label:"Rain %",data:rain,yAxisID:"y1",tension:.35,borderWidth:1.5,pointRadius:0,borderColor:"#b18cff"}
    ]},
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:"index",intersect:false},
      plugins:{legend:{display:false}},
      scales:{
        x:{grid:{display:false},ticks:{color:"#a995b8",maxTicksLimit:8}},
        y:{position:"left",grid:{color:"rgba(255,255,255,.05)"},ticks:{color:"#a995b8",callback:v=>v+"°"}},
        y1:{position:"right",min:0,max:100,grid:{display:false},ticks:{color:"#a995b8",callback:v=>v+"%"}}
      }
    }
  });
}

function renderDaily(d,labels){
  const times=d.time || [];
  $("dailyGrid").innerHTML=times.map((date,i)=>`
    <article class="day-card">
      <div class="day">${dayLabel(date,i)}</div>
      <div class="date">${new Date(date+"T12:00:00").toLocaleDateString("en-US",{month:"short",day:"numeric"})}</div>
      <div class="icon">${iconFor(d.weather_code?.[i],1)}</div>
      <div class="desc">${esc(labels[i] || "Weather")}</div>
      <div class="temps"><b>${moneyless(d.temperature_2m_max?.[i])}°</b><span>${moneyless(d.temperature_2m_min?.[i])}°</span></div>
      <div class="rain">☂ ${moneyless(d.precipitation_probability_max?.[i])}% • wind ${moneyless(d.wind_speed_10m_max?.[i])} km/h</div>
    </article>
  `).join("");
}

async function loadWeather(params){
  setLoading(true);
  try{
    const data=await fetchWeatherDirect(params);
    render(data);
    if(params.city) localStorage.setItem("weather_city", params.city);
  }catch(e){
    showError(e.message || "Weather request failed.");
  }finally{
    setLoading(false);
  }
}

async function doSearch(){
  const city=$("cityInput").value.trim();
  if(city.length<2) return showError("Enter a city name.");
  $("suggestions").classList.remove("show");
  await loadWeather({city});
}

$("searchBtn").addEventListener("click",doSearch);
$("cityInput").addEventListener("keydown",e=>{if(e.key==="Enter") doSearch();});
$("cityInput").addEventListener("input",()=>{
  clearTimeout(debounceTimer);
  const q=$("cityInput").value.trim();
  if(q.length<3){$("suggestions").classList.remove("show");return;}
  debounceTimer=setTimeout(async()=>{
    try{
      const u=new URL("https://geocoding-api.open-meteo.com/v1/search");
      u.search=new URLSearchParams({name:q,count:"6",language:"en",format:"json"}).toString();
      const r=await fetch(u);
      const data=await r.json();
      const rows=data.results||[];
      $("suggestions").innerHTML=rows.map(function(x){
        return '<div class="suggestion" data-name="'+esc(x.name)+'"><b>'+esc(x.name)+'</b><small>'+esc([x.admin1,x.country].filter(Boolean).join(", "))+'</small></div>';
      }).join("");
      $("suggestions").classList.toggle("show",rows.length>0);
      document.querySelectorAll(".suggestion").forEach(function(el){
        el.addEventListener("click",function(){
          $("cityInput").value=el.dataset.name;
          $("suggestions").classList.remove("show");
          loadWeather({city:el.dataset.name});
        });
      });
    }catch(e){}
  },320);
});

$("locationBtn").addEventListener("click",()=>{
  if(!navigator.geolocation) return showError("Geolocation is not supported by this browser.");
  setLoading(true);
  navigator.geolocation.getCurrentPosition(
    pos=>loadWeather({lat:pos.coords.latitude,lon:pos.coords.longitude}),
    ()=>{setLoading(false);showError("Location permission was not available. Search for your city instead.");},
    {enableHighAccuracy:true,timeout:9000}
  );
});

$("menuBtn").addEventListener("click",()=> $("sidebar").classList.toggle("open"));
document.querySelectorAll("[data-jump]").forEach(b=>b.addEventListener("click",()=>{
  document.querySelectorAll(".nav-item").forEach(x=>x.classList.remove("active"));
  b.classList.add("active");
  $(b.dataset.jump).scrollIntoView({behavior:"smooth"});
  $("sidebar").classList.remove("open");
}));

document.addEventListener("click",e=>{
  if(!e.target.closest(".search-wrap")) $("suggestions").classList.remove("show");
});

const initial=localStorage.getItem("weather_city") || "Ahmedabad";
$("cityInput").value=initial;
loadWeather({city:initial});
