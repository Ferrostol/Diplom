--
-- PostgreSQL database dump
--

-- Dumped from database version 9.3.16
-- Dumped by pg_dump version 14.2

-- Started on 2022-06-26 21:15:14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE test;
--
-- TOC entry 2331 (class 1262 OID 16385)
-- Name: test; Type: DATABASE; Schema: -; Owner: -
--

CREATE DATABASE test WITH TEMPLATE = template0 ENCODING = 'UTF8' LC_COLLATE = 'C' LC_CTYPE = 'ru_RU.UTF-8';


\connect test

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 195 (class 1255 OID 16519)
-- Name: checkbeforeaddnewswitch(integer, integer, character varying, character varying, integer, boolean, numeric, numeric, numeric, character varying, character varying, boolean); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.checkbeforeaddnewswitch(newid integer, newmodel_id integer, newname character varying, newip character varying, newport integer, newstatus boolean, newx numeric, newy numeric, newz numeric, newcommunity character varying, newproc character varying, newidleproc boolean) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN 
    if NOT EXISTS (select * from switches where id=Newid) then
            insert into switches (model_id,ip,port,status,name) values (Newmodel_id,Newip,Newport,Newstatus,Newname);
            insert into mibslist (switches_id,proc,idleproc,community) values ((select id from switches where ip=Newip),Newproc,Newidleproc,Newcommunity);
            insert into switches_position (switches_id,x,y,z) values ((select id from switches where ip=Newip),Newx,Newy,Newz);
    else
            update switches set ip=Newip, port=Newport,status=Newstatus,name=Newname where id=Newid;
                if NOT EXISTS (select * from mibslist where switches_id=Newid) then
                    insert into mibslist (switches_id,proc,idleproc,community) values (Newid,Newproc,Newidleproc,Newcommunity);
                else
                    update mibslist set proc=Newproc, idleproc=Newidleproc, community=Newcommunity where switches_id=Newid;
                end IF;
   

                if NOT EXISTS (select * from switches_position where switches_id=Newid) then
                        insert into switches_position (switches_id,x,y,z) values (Newid,Newx,Newy,Newz);
                else 
                        update switches_position set x=Newx, y=Newy, z=Newz where switches_id=Newid;
                END if;
    END if;
    return true;
END;
$$;


--
-- TOC entry 196 (class 1255 OID 16593)
-- Name: updatelastporterror(integer, integer, integer, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.updatelastporterror(switch_id integer, new_num_port integer, new_error_in integer, new_error_out integer) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN 
    if NOT EXISTS (select * from lastporterror where switches_id=switch_id and num_port = new_num_port) then
            insert into lastporterror (switches_id, num_port, error_in, error_out) 
			values (switch_id, new_num_port, new_error_in, new_error_out);
    else
            update lastporterror set error_in=new_error_in, error_out=new_error_out 
			where switches_id=switch_id and num_port = new_num_port;
    END if;
    return true;
END;
$$;


--
-- TOC entry 179 (class 1259 OID 16540)
-- Name: error_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.error_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 176 (class 1259 OID 16476)
-- Name: error; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.error (
    id_errors integer DEFAULT nextval('public.error_id_seq'::regclass) NOT NULL,
    date timestamp without time zone DEFAULT now() NOT NULL,
    id_swit integer,
    id_err_info integer,
    description text
);


--
-- TOC entry 175 (class 1259 OID 16449)
-- Name: errorlist; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.errorlist (
    id integer NOT NULL,
    info text NOT NULL
);


--
-- TOC entry 182 (class 1259 OID 16582)
-- Name: lastporterror; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lastporterror (
    switches_id integer NOT NULL,
    num_port integer NOT NULL,
    error_in integer,
    error_out integer
);


--
-- TOC entry 173 (class 1259 OID 16408)
-- Name: mibslist; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mibslist (
    switches_id integer NOT NULL,
    proc character varying(100),
    idleproc boolean DEFAULT false NOT NULL,
    community character varying(100),
    temp character varying(100)
);


--
-- TOC entry 171 (class 1259 OID 16391)
-- Name: model; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model (
    id integer NOT NULL,
    name character varying(60)
);


--
-- TOC entry 177 (class 1259 OID 16495)
-- Name: statcpu; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.statcpu (
    switches_id integer NOT NULL,
    datevrem timestamp without time zone DEFAULT now() NOT NULL,
    procent numeric(5,2)
);


--
-- TOC entry 181 (class 1259 OID 16564)
-- Name: statport; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.statport (
    switches_id integer NOT NULL,
    datevrem timestamp without time zone DEFAULT now() NOT NULL,
    num_port integer NOT NULL,
    error_in integer,
    error_out integer
);


--
-- TOC entry 180 (class 1259 OID 16542)
-- Name: stattemp; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stattemp (
    switches_id integer NOT NULL,
    datevrem timestamp without time zone DEFAULT now() NOT NULL,
    num_sensor integer NOT NULL,
    value numeric(5,2)
);


--
-- TOC entry 172 (class 1259 OID 16396)
-- Name: switches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.switches (
    id integer NOT NULL,
    model_id integer,
    ip character varying(30) NOT NULL,
    port integer DEFAULT 161 NOT NULL,
    status boolean DEFAULT false NOT NULL,
    name character varying(60)
);


--
-- TOC entry 178 (class 1259 OID 16508)
-- Name: switches_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.switches_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2332 (class 0 OID 0)
-- Dependencies: 178
-- Name: switches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.switches_id_seq OWNED BY public.switches.id;


--
-- TOC entry 174 (class 1259 OID 16419)
-- Name: switches_position; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.switches_position (
    switches_id integer NOT NULL,
    x numeric(8,2) NOT NULL,
    y numeric(8,2) NOT NULL,
    z numeric(8,2) NOT NULL
);


--
-- TOC entry 2181 (class 2604 OID 16510)
-- Name: switches id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.switches ALTER COLUMN id SET DEFAULT nextval('public.switches_id_seq'::regclass);


--
-- TOC entry 2201 (class 2606 OID 16484)
-- Name: error error_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.error
    ADD CONSTRAINT error_pkey PRIMARY KEY (id_errors);


--
-- TOC entry 2199 (class 2606 OID 16456)
-- Name: errorlist errorlist_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.errorlist
    ADD CONSTRAINT errorlist_pkey PRIMARY KEY (id);


--
-- TOC entry 2209 (class 2606 OID 16586)
-- Name: lastporterror lastporterror_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lastporterror
    ADD CONSTRAINT lastporterror_pkey PRIMARY KEY (switches_id, num_port);


--
-- TOC entry 2195 (class 2606 OID 16413)
-- Name: mibslist mibslist_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mibslist
    ADD CONSTRAINT mibslist_pkey PRIMARY KEY (switches_id);


--
-- TOC entry 2189 (class 2606 OID 16395)
-- Name: model model_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model
    ADD CONSTRAINT model_pkey PRIMARY KEY (id);


--
-- TOC entry 2203 (class 2606 OID 16499)
-- Name: statcpu statcpu_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statcpu
    ADD CONSTRAINT statcpu_pkey PRIMARY KEY (switches_id, datevrem);


--
-- TOC entry 2207 (class 2606 OID 16569)
-- Name: statport statport_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statport
    ADD CONSTRAINT statport_pkey PRIMARY KEY (switches_id, datevrem, num_port);


--
-- TOC entry 2205 (class 2606 OID 16547)
-- Name: stattemp stattemp_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stattemp
    ADD CONSTRAINT stattemp_pkey PRIMARY KEY (switches_id, datevrem, num_sensor);


--
-- TOC entry 2191 (class 2606 OID 16514)
-- Name: switches switches_ip_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.switches
    ADD CONSTRAINT switches_ip_key UNIQUE (ip);


--
-- TOC entry 2193 (class 2606 OID 16402)
-- Name: switches switches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.switches
    ADD CONSTRAINT switches_pkey PRIMARY KEY (id);


--
-- TOC entry 2197 (class 2606 OID 16423)
-- Name: switches_position switches_position_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.switches_position
    ADD CONSTRAINT switches_position_pkey PRIMARY KEY (switches_id);


--
-- TOC entry 2213 (class 2606 OID 16490)
-- Name: error error_id_err_info_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.error
    ADD CONSTRAINT error_id_err_info_fkey FOREIGN KEY (id_err_info) REFERENCES public.errorlist(id);


--
-- TOC entry 2214 (class 2606 OID 16535)
-- Name: error error_id_swit_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.error
    ADD CONSTRAINT error_id_swit_fkey FOREIGN KEY (id_swit) REFERENCES public.switches(id) ON DELETE CASCADE;


--
-- TOC entry 2218 (class 2606 OID 16587)
-- Name: lastporterror lastporterror_switches_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lastporterror
    ADD CONSTRAINT lastporterror_switches_id_fkey FOREIGN KEY (switches_id) REFERENCES public.switches(id) ON DELETE CASCADE;


--
-- TOC entry 2211 (class 2606 OID 16520)
-- Name: mibslist mibslist_switches_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mibslist
    ADD CONSTRAINT mibslist_switches_id_fkey FOREIGN KEY (switches_id) REFERENCES public.switches(id) ON DELETE CASCADE;


--
-- TOC entry 2215 (class 2606 OID 16525)
-- Name: statcpu statcpu_switches_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statcpu
    ADD CONSTRAINT statcpu_switches_id_fkey FOREIGN KEY (switches_id) REFERENCES public.switches(id) ON DELETE CASCADE;


--
-- TOC entry 2217 (class 2606 OID 16570)
-- Name: statport statport_switches_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statport
    ADD CONSTRAINT statport_switches_id_fkey FOREIGN KEY (switches_id) REFERENCES public.switches(id) ON DELETE CASCADE;


--
-- TOC entry 2216 (class 2606 OID 16548)
-- Name: stattemp stattemp_switches_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stattemp
    ADD CONSTRAINT stattemp_switches_id_fkey FOREIGN KEY (switches_id) REFERENCES public.switches(id);


--
-- TOC entry 2210 (class 2606 OID 16403)
-- Name: switches switches_model_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.switches
    ADD CONSTRAINT switches_model_id_fkey FOREIGN KEY (model_id) REFERENCES public.model(id);


--
-- TOC entry 2212 (class 2606 OID 16530)
-- Name: switches_position switches_position_switches_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.switches_position
    ADD CONSTRAINT switches_position_switches_id_fkey FOREIGN KEY (switches_id) REFERENCES public.switches(id) ON DELETE CASCADE;


-- Completed on 2022-06-26 21:15:39

--
-- PostgreSQL database dump complete
--

