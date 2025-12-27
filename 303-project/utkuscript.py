.day-card{
  background:#f4f6f8;
  border-radius:18px;
  padding:18px;
  text-align:center;
  position:relative;
  overflow:hidden;
  cursor:pointer;
  transition: 
    transform .35s ease,
    box-shadow .35s ease,
    background .35s ease;
}

/* Hover büyüme + gölge */
.day-card:hover{
  transform:translateY(-10px) scale(1.04);
  box-shadow:0 20px 35px rgba(0,0,0,.22);
}

/* Işık geçiş efekti */
.day-card::after{
  content:"";
  position:absolute;
  inset:0;
  background:linear-gradient(
    120deg,
    transparent,
    rgba(255,255,255,.7),
    transparent
  );
  transform:translateX(-130%);
  transition:.7s;
}
.day-card:hover::after{
  transform:translateX(130%);
}

/* İkon animasyonu */
.day-card:hover .icon{
  animation:float 1.5s ease-in-out infinite;
}

@keyframes float{
  0%{transform:translateY(0)}
  50%{transform:translateY(-8px)}
  100%{transform:translateY(0)}
}

/* Seçilen gün */
.day-card.active{
  background:#6a7cf7 !important;
  color:white;
}
.day-card.active .desc{
  opacity:.9;
}
